# Copyright (c) 2025 Huawei Technologies Co., Ltd. All rights reserved.
# Copyright (c) 2026 South China Sea Institute of Oceanology, Chinese Academy of Sciences (SCSIO, CAS). All rights reserved.
import json
import logging
from turtle import end_fill
from typing import Dict, Any, List, Optional, Union
import litellm
from pathlib import Path
import time
import requests
import os
from .base_agent import BaseAgent, AgentConfig, AgentResponse, TaskInput
from .. import llm_client

logger = logging.getLogger(__name__)



class InformationSeekerAgent(BaseAgent):
    """
    Information Seeker Agent that follows ReAct pattern (Reasoning + Acting)
    
    This agent takes decomposed sub-questions or tasks from parent agents,
    thinks interleaved (reasoning -> action -> reasoning -> action),
    uses MCP tools to gather information, and returns structured results.
    """

    def __init__(self, config: AgentConfig = None, shared_mcp_client=None):
        # Set default agent name if not specified
        if config is None:
            config = AgentConfig(agent_name="InformationSeekerAgent")
        elif config.agent_name == "base_agent":
            config.agent_name = "InformationSeekerAgent"
            
        super().__init__(config, shared_mcp_client)
    
    def set_cancellation_token(self, cancellation_token):
        """
        Set the cancellation token for this agent
        设置此代理的取消令牌
        
        Args:
            cancellation_token: threading.Event object that will be set when task should be cancelled
        """
        self._cancellation_token = cancellation_token
    
    def _check_cancellation(self) -> bool:
        """
        Check if task has been cancelled
        检查任务是否已被取消
        
        Returns:
            True if task should be cancelled, False otherwise
        """
        if self._cancellation_token and self._cancellation_token.is_set():
            self.logger.info("InformationSeekerAgent task cancellation detected")
            return True
        return False
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the ReAct agent"""
        tool_schemas_str = json.dumps(self.tool_schemas, ensure_ascii=False)
        system_prompt_template = """You are an Information Seeker Agent that follows the ReAct pattern (Reasoning + Acting).
        
        Your role is to:
        1. Take decomposed sub-questions or tasks from parent agents
        2. Think step-by-step through reasoning 
        3. Use available tools to gather information when needed
        4. Continue reasoning based on tool results
        5. Repeat this process until you have sufficient information
        6. Call info_seeker_objective_task_done to provide a structured summary
        
        ### Optimized Workflow:
        Follow this optimized workflow for information gathering:
        
		0. **MANDATORY FIRST STEP - Check Workspace for Existing Files:**
		   - Check `./user_uploads/` directory for user-uploaded files (HIGH PRIORITY)
		   - Check `./library_refs/` directory for user-selected library files (NORMAL PRIORITY)
		   - **CRITICAL REQUIREMENT:** When calling `document_extract`, you MUST include ALL document files from BOTH directories:
		     * Include ALL .pdf, .doc, .docx files (source documents)
		     * Include ALL .txt files that are NOT converted from other documents (e.g., research/*.txt)
		     * The system will automatically skip .pdf.txt, .doc.txt, .docx.txt if the source file exists
		   - **DO NOT FILTER FILES:** Do NOT make assumptions about file relevance based on filenames
		   - **DO NOT SELECT SUBSET:** Do NOT choose only "relevant-looking" files - analyze ALL files
		   - **MANDATORY:** If library_refs has 12 files, you MUST pass all 12 files to document_extract
		   - **CRITICAL:** Do NOT skip library_refs files even if user_uploads has files
		   - Only proceed to web search after analyzing existing files

		1. INITIAL RESEARCH:
		   - Generate focused search queries (≤10): Limit to no more than 10 initial search queries to avoid increased failure rates from excessive decomposition.
		   - Analyse and select the appropriate information retrieval tools to get relevant information for your queries, based on the tool description. You can split a query into multiple tool-invoked inputs based on the tool description. Use the professional search tools for biology-related articles("search_pubmed_key_words", "search_pubmed_advanced","medrxiv_search"), and professional computer-science-related article search tools for CS knowledge.("arxiv_search"). The web search engine is a general retrieval tool for any query ("batch_web_search"). When calling the web search engine, consider the language of the user's question. For example, for a Chinese question, generate a part of the search statement in Chinese. But for other tools, pay attention to the requests in thier descriptions.
		   - Analyze the search results (titles, snippets, URLs, article id, article abstract...) to identify promising sources

		2. CONTENT EXTRACTION:  
		   - For important URLs searched by "batch_web_search", use `jina_reader` to extract full content from the webpage. 
		   - For important articles searched with pubmed, medrxiv, or arxiv, use "get_pubmed_article", "medrxiv_read_paper", "arxiv_read_paper" to extract full content.
		   - Save the content to a file in the workspace **under the relative path `./research/`**  
		   - Store results with meaningful file paths (e.g., "./research/ai_trends_2024.txt")
        
        3. CONTENT ANALYSIS:
           - Use `document_qa` to ask specific questions about the saved files:
                a) Formulate focused questions to extract key insights
                b) Use answers to deepen your understanding
           - You can ask multiple questions about the same file
           - Use `document_extract` for multi-dimensional analysis of saved files:
        		a) Provides structured analysis across five key dimensions: doc time, source, authority, core content and task relevance.

        4. FILE MANAGEMENT:
           - Use `file_write` to save important findings or summaries
           - For reviewing saved content:
                a) Prefer `document_qa` to ask specific questions about the content
				b) Prefer `document_extract` to get comprehensive multi-dimensional analysis of saved files
                c) Use `file_read` ONLY for small files (<1000 tokens) when you need the entire content
                d) Avoid reading large files directly as it may exceed context limits
        
        5. TASK COMPLETION:
           - When ready to report, call `info_seeker_objective_task_done` with:
                a) Comprehensive markdown summary of your process and findings
                b) List of key files created with descriptions
        
        ### Usage of Systematic Tool:
            - `think` is a systematic tool. After receiving the response from the complex tool or before invoking any other tools, you must **first invoke the `think` tool**: to deeply reflect on the results of previous tool invocations (if any), and to thoroughly consider and plan the user's task. The `think` tool does not acquire new information; it only saves your thoughts into memory.
            - `reflect` is a systematic tool. When encountering a failure in tool execution, it is necessary to invoke the reflect tool to conduct a review and revise the task plan. It does not acquire new information; it only saves your thoughts into memory.
        
        Always provide clear reasoning for your actions and synthesize information effectively.
"""
        return system_prompt_template.replace("$tool_schemas", tool_schemas_str)

    @staticmethod
    def _build_initial_message_from_task_input(task_input: TaskInput) -> str:
        """Build the initial user message from TaskInput"""
        message = task_input.format_for_prompt()
        
        message += "\nPlease analyze this task and start your ReAct process:\n"
        message += "1. Reason about what information you need to gather\n"
        message += "2. Use appropriate tools to get that information\n"
        message += "3. Continue reasoning and acting until you have sufficient information\n"
        message += "4. Call task_done when ready to provide your complete findings\n\n"
        message += "Begin with your initial reasoning about the task."
        
        return message
    
    def execute_task(self, task_input: TaskInput) -> AgentResponse:
        """
        Execute a task using ReAct pattern (Reasoning + Acting)
        
        Args:
            task_input: TaskInput object with standardized task information
            
        Returns:
            AgentResponse with results and process trace
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting information seeker task: {task_input.task_content}")
            
            # Reset trace for new task
            self.reset_trace()
            
            # Initialize conversation history
            conversation_history = []
            
            # Build initial system prompt for ReAct
            system_prompt = self._build_system_prompt()
            
            # Build initial user message from TaskInput
            user_message = self._build_initial_message_from_task_input(task_input)
            
            
            # Add to conversation
            conversation_history.append({"role": "system", "content": system_prompt})
            conversation_history.append({"role": "user", "content": user_message+" /no_think"})

            
            iteration = 0
            task_completed = False
            # Get model endpoint configuration from env-backed config
            from config.config import get_config
            config = get_config()
            model_config = config.get_custom_llm_config()

            pangu_url = model_config.get('url') or os.getenv('MODEL_REQUEST_URL', '')
            headers = llm_client.get_headers(model_config)
            openai_tools = None
            if llm_client.is_deepseek_api(model_config):
                schemas = self.get_tool_schemas_for_prompt()
                openai_tools = llm_client.mcp_schemas_to_openai_tools(schemas, list(self.available_tools.keys()))

            # ReAct Loop: Reasoning -> Acting -> Reasoning -> Acting...
            while iteration < self.config.max_iterations and not task_completed:
                iteration += 1
                self.logger.info(f"Planning iteration {iteration}")
                
                try:
                    retry_num = 1
                    max_retry_num = 10
                    while retry_num < max_retry_num:
                        try:
                            body = llm_client.build_chat_request(
                                model_config,
                                conversation_history,
                                temperature=self.config.temperature,
                                max_tokens=self.config.max_tokens,
                                tools=openai_tools,
                            )
                            response = requests.post(
                                url=pangu_url,
                                headers=headers,
                                json=body,
                                timeout=model_config.get("timeout", 180)
                            )
                            response = response.json()
                            self.logger.debug(f"API response received")
                            break
                        except Exception as e:
                            time.sleep(3)
                            retry_num += 1
                            if retry_num == max_retry_num:
                                raise ValueError(str(e))
                            continue

                    assistant_message, tool_calls = llm_client.parse_chat_response(response, model_config)

                    reasoning_content = llm_client.extract_reasoning_from_content(assistant_message.get("content"))
                    if reasoning_content:
                        self.log_reasoning(iteration, reasoning_content)
                    if not assistant_message.get("content") and not tool_calls:
                        followup_prompt = "There is a problem with the format of model generation. Please try again."
                        conversation_history.append({"role": "user", "content": followup_prompt + " /no_think"})
                        continue

                    conversation_history.append(assistant_message)

                    tool_results = []
                    for tool_call in tool_calls:
                        arguments = tool_call.get("arguments") or {}
                        if isinstance(arguments, str):
                            try:
                                arguments = json.loads(arguments) if arguments.strip() else {}
                            except json.JSONDecodeError:
                                arguments = {}

                        if tool_call.get("name") in ["info_seeker_objective_task_done"]:
                            task_completed = True
                            self.log_action(iteration, tool_call["name"], arguments, arguments)
                            tool_results.append(arguments)
                            break
                        if tool_call.get("name") in ["think", "reflect"]:
                            tool_result = {"tool_results": "You can proceed to invoke other tools if needed."}
                        else:
                            tool_result = self.execute_tool_call({"name": tool_call["name"], "arguments": arguments})

                        tool_results.append(tool_result)
                        self.log_action(iteration, tool_call["name"], arguments, tool_result)

                    n_executed = len(tool_results)
                    conversation_history.extend(
                        llm_client.build_tool_result_messages(tool_calls[:n_executed], tool_results, model_config, suffix=" /no_think")
                    )
                    
                    if len(tool_calls) == 0:
                        # Add follow-up prompt to encourage action or completion
                        followup_prompt = (
                            "Continue your planning process. Use available tools to assign tasks to agents, "
                            "search for information, or coordinate work. When you have a complete answer, "
                            "call info_seeker_objective_task_done. /no_think"
                        )
                        conversation_history.append({"role": "user", "content": followup_prompt})
                    if iteration == self.config.max_iterations-3:
                        followup_prompt = "Due to length and number of rounds restrictions, you must now call the `info_seeker_objective_task_done` tool to report the completion of your task. /no_think"
                        conversation_history.append({"role": "user", "content": followup_prompt})                        
                    
                    
                except Exception as e:
                    error_msg = f"Error in planning iteration {iteration}: {e}"
                    self.log_error(iteration, error_msg)
                    break
            
            execution_time = time.time() - start_time
            # Extract final result
            if task_completed:
                # Find the info_seeker_objective_task_done result in the trace
                task_done_result = None
                for step in reversed(self.reasoning_trace):
                    if step.get("type") == "action" and step.get("tool") == "info_seeker_objective_task_done":
                        task_done_result = step.get("result")
                        break
                
                return self.create_response(
                    success=True,
                    result=task_done_result,
                    iterations=iteration,
                    execution_time=execution_time
                )
            else:
                return self.create_response(
                    success=False,
                    error=f"Task not completed within {self.config.max_iterations} iterations",
                    iterations=iteration,
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Error in execute_task: {e}")
            return self.create_response(
                success=False,
                error=str(e),
                iterations=iteration if 'iteration' in locals() else 0,
                execution_time=execution_time
            )

    def _build_agent_specific_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Build tool schemas for InformationSeekerAgent using proper MCP architecture.
        Schemas come from MCP server via client, not direct imports.
        """

        # Get MCP tool schemas from server via client (proper MCP architecture)
        schemas = super()._build_agent_specific_tool_schemas()

        # Add schemas for built-in task assignment tools
        builtin_assignment_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "think",
                    "description": "Use the tool to think about something. It will not obtain new information or make any changes to the repository, but just log the thought. Use it when complex reasoning or brainstorming is needed.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "thought": {
                                "type": "string",
                                "description": "Your thoughts."
                            }
                        },
                        "required": ["thought"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "reflect",
                    "description": "When multiple attempts yield no progress, use this tool to reflect on previous reasoning and planning, considering possible overlooked clues and exploring more possibilities. It will not obtain new information or make any changes to the repository.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reflect": {
                                "type": "string",
                                "description": "The specific content of your reflection"
                            }
                        },
                        "required": ["reflect"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "info_seeker_objective_task_done",
                    "description": "Structured reporting of task completion details including summary, decisions, outputs, and status",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "task_summary": {
                                "type": "string",
                                "description": "Comprehensive markdown covering what the agent was asked to do, steps taken, tools used, key findings, files created, challenges, and final deliverables.",
                                "format": "markdown"
                            },
                            "task_name": {
                                "type": "string",
                                "description": "The name of the task currently assigned to the agent, usually with underscores (e.g., 'web_research_ai_trends')"
                            },
                            "key_files": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {
                                            "type": "string",
                                            "description": "Relative path to created/modified file"
                                        },
                                        "desc": {
                                            "type": "string",
                                            "description": "File contents and creation purpose"
                                        },
                                        "is_final_output_file": {
                                            "type": "boolean",
                                            "description": "Whether file is primary deliverable"
                                        }
                                    },
                                    "required": ["file_path", "desc", "is_final_output_file"]
                                },
                                "description": "List of key files generated or modified during the task, with their details."
                            },
                            "completion_status": {
                                "type": "string",
                                "enum": ["completed", "partial", "failed"],
                                "description": "Final task status"
                            }
                        },
                        "required": ["task_summary", "task_name", "key_files", "completion_status"]
                    }
                }
            },
        ]

        schemas.extend(builtin_assignment_schemas)

        return schemas


# Factory function for creating the agent
def create_objective_information_seeker(
    model: Any = None,
    max_iterations: Any = None,
    shared_mcp_client=None,
    **kwargs
) -> InformationSeekerAgent:
    """
    Create an InformationSeekerAgent instance with server-managed sessions.
    
    Args:
        model: The LLM model to use
        max_iterations: Maximum number of iterations
        shared_mcp_client: Optional shared MCP client from parent agent (prevents extra sessions)
        **kwargs: Additional configuration options
        
    Returns:
        Configured InformationSeekerAgent instance with appropriate tools
    """
    # Import the enhanced config function
    from ..agents.base_agent import create_agent_config
    
    # Create agent configuration (session managed by MCP server)
    config = create_agent_config(
        agent_name="InformationSeekerAgent",
        model=model,
        max_iterations=max_iterations,
        **kwargs
    )
    
    # Create agent instance with shared MCP client (filtered tools for information seeking)
    agent = InformationSeekerAgent(config=config, shared_mcp_client=shared_mcp_client)
    
    return agent
