# Copyright (c) 2025 Huawei Technologies Co., Ltd. All rights reserved.
# Copyright (c) 2026 South China Sea Institute of Oceanology, Chinese Academy of Sciences (SCSIO, CAS). All rights reserved.
import json
from typing import Dict, Any, List
import time
import requests
import os
from .base_agent import BaseAgent, AgentConfig, AgentResponse, WriterAgentTaskInput
from .. import llm_client



class WriterAgent(BaseAgent):
    """
    Writer Agent that follows ReAct pattern for content synthesis and generation
    
    This agent takes writing tasks from parent agents, searches through existing
    files and knowledge base, and creates long-form content through iterative
    reasoning and refinement. It does NOT access internet resources, only
    local files and memories.
    """

    def __init__(self, config: AgentConfig = None, shared_mcp_client=None):
        # Set default agent name if not specified
        if config is None:
            config = AgentConfig(agent_name="WriterAgent")
        elif config.agent_name == "base_agent":
            config.agent_name = "WriterAgent"

        super().__init__(config, shared_mcp_client)

        # Rebuild tool schemas with writer-specific tools only
        self.tool_schemas = self._build_tool_schemas()
        # Cancellation support
        self._cancellation_token = None

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
            self.logger.info("WriterAgent task cancellation detected")
            return True
        return False

    def _build_agent_specific_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Build tool schemas for WriterAgent using proper MCP architecture.
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
                    "name": "writer_subjective_task_done",
                    "description": "Writer Agent task completion reporting for complete long-form content. Called after all chapters/sections are written to provide a summary of the complete long article, final completion status and analysis, and the storage path of the final consolidated article.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "final_article_path": {
                                "type": "string",
                                "description": "The file path where the final article is saved."
                            },
                            "article_summary": {
                                "type": "string",
                                "description": "Comprehensive summary of the complete long-form article, including main themes, key points covered, and overall narrative structure.",
                                "format": "markdown"
                            },
                            "completion_status": {
                                "type": "string",
                                "enum": ["completed", "partial", "failed"],
                                "description": "Final status of the complete long-form writing task"
                            },
                            "completion_analysis": {
                                "type": "string",
                                "description": "Analysis of the overall writing project completion including: assessment of article coherence and quality, evaluation of content organization and flow, identification of any challenges in the writing process, and overall evaluation of the long-form content creation success."
                            }
                        },
                        "required": ["final_article_path", "article_summary", "completion_status",
                                     "completion_analysis"]
                    }
                }
            },
        ]

        schemas.extend(builtin_assignment_schemas)

        return schemas

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the writer agent"""
        tool_schemas_str = json.dumps(self.tool_schemas, ensure_ascii=False)
        system_prompt_template = """You are a professional writing master. You will receive key files and user problems. Your task is to generate an outline highly consistent with the user problem, classify files into sections, and iteratively call section_writer tool to create comprehensive content. Then you strictly follow the steps given below:
        
        MANDATORY WORKFLOW:
        
        1. OUTLINE GENERATION
        Based on the core content of the provided key files collection(file_core_content), generate a high-quality outline suitable for long-form writing. Strictly adhere to the following requirements during generation:  
        - Before generating the outline, carefully review the provided **file_core_content**, prioritizing sections with:  
            1.**Higher authority** (credible sources)
            2.**Greater information richness** (substantive, detailed content)
            3.**Stronger relevance** (direct alignment with user query)
            4.**Timeliness** (if user’s query is time-sensitive, prioritize recent/updated content)
        Select these segments as the basis for outline generation. Note that we only focus on relevance to the question, so when generating the outline, do not add unrelated sections just for the sake of length. Additionally, the sections should flow logically and not be too disjointed, as this would harm the readability of the final output.  
        - The overall structure must be **logically clear**, with **no repetition or redundancy** between chapters.  
        - **Note1:** The generated outline must not only have chapter-level headings (Level 1) highly relevant to the user’s question, but the subheadings (Level 2) must also be highly relevant to the user’s question. It is not permitted to generate chapter titles with weak relevance, whether Level 1 or Level 2.
        - **Note2:** The number of chapters must not exceed 7, dynamic evaluation can be performed based on the collected content. For example, if there is a lot of content, more chapters can be generated, and vice versa. But each chapter should only include Level 1 and Level 2 headings. Also, be careful not to generate too many Level 2 headings, limit them to 4. However, if the first chapter is an abstract or introduction, do not generate subheadings (level-2 headings)—only include the main heading (level-1). Additionally, tailor the outline style based on the type of document. For example, in a research report, the first chapter should preferably be titled \"Abstract\" or \"Introduction.\"  
        
        2. FILE CLASSIFICATION  
        - Use the search_result_classifier tool to reasonably split the outline generated above and accurately assign key files to each chapter of the outline.
        - Ensure optimal distribution of reference materials across chapters based on content relevance.
        
        3. ITERATIVE SECTION WRITING
        - Call section_writer tool sequentially for each chapter
        - CRITICAL: Must wait for previous chapter completion before starting the next chapter
        - Pass only the specific chapter outline , target file path and corresponding classified files to each section writer
        - Generate save path for each chapter using \"./report/part_X.md\" format (e.g., \"./report/part_1.md\" for first chapter)
        - Check section writer results after completion; retry up to 2 times per chapter if quality is insufficient based on returned fields (do not read saved files)
        - When you call the section_writer tool, pay special attention to the fact that the parameter value of written_chapters_summary is a summary of the content returned by all previously completed chapters. Be careful not to make any changes to the summary content, including compressing the content.
        
        4. TASK COMPLETION
        - After all chapters are written, you must first call the concat_section_files tool to merge the saved chapter files into one file, then call writer_subjective_task_done to finalize and return.
        
        CRITICAL REQUIREMENTS:
        - The creation of the outline is crucial! Therefore, you must strictly adhere to the above requirements for generating the outline.
        - No parallel writing - strictly sequential chapter execution
        - Wait for each section writer completion before proceeding to next chapter
        - Classify files appropriately to support each chapter's content needs
        - Note again that to merge all the written chapter files, you must use the concat_section_files tool!!! You are not allowed to call any other tools for merging!!!
        
        FORBIDDEN CONTENT PATTERNS:
        - NEVER generate meta-structural chapters that describe how the article is organized
        - AVOID introductory sections that outline \"Chapter 1 will cover..., Chapter 2 will discuss...\"
        - DO NOT create chapters that explain the report structure or methodology
        - Each chapter must contain SUBSTANTIVE CONTENT, not descriptions of what other chapters contain
        - When generating an outline, if it is not a professional term, the language should remain consistent with the user's question.\"
        
        Usage of TOOLS:
        - search_result_classifier: Classify key files into outline sections
        - section_writer: Write individual chapters sequentially  
        - writer_subjective_task_done: Complete the writing task
        - concat_section_files: Concatenate the content of the saved section files into a single file
        - think tool: \"Think\" is a systematic tool requiring its use during key steps. Before executing actions like generating an outline, you must first call this tool to deeply consider the given content and key requirements, ensuring the output meets specifications. Similarly, during iterative chapter generation, after receiving feedback and before writing the next chapter, call \"think\" to reflect on the current chapter. This provides guidance to avoid content repetition and ensure smooth transitions between chapters.
        
        Execute workflow systematically to produce high-quality, coherent long-form content with substantive chapters.
"""
        return system_prompt_template.replace("$tool_schemas", tool_schemas_str)

    def _build_initial_message_from_task_input(self, task_input: WriterAgentTaskInput) -> str:
        """Build the initial user message from TaskInput"""
        message = ""

        # Add key files information with reliability dimensions
        def load_json_from_server(file_path):
            """Load JSONL file from MCP server using unlimited internal tool"""
            res = []
            try:
                # Use json read tool directly through raw MCP client
                raw_result = self.mcp_tools.client.call_tool("load_json", {"file_path": file_path})
                
                if not raw_result.success:
                    self.logger.error(f"Failed to read file from server: {raw_result.error}")
                    return res
                
                res = json.loads(raw_result.data["content"][0]["text"])["data"]
                                            
            except Exception as e:
                self.logger.error(f"Error loading file {file_path} from MCP server: {e}")
                import traceback
                self.logger.debug(f"Full traceback: {traceback.format_exc()}")
                
            return res

        key_files_dict = {}

        server_analysis_path = f"doc_analysis/file_analysis.jsonl"
        self.logger.debug(f"Loading analysis from MCP server: {server_analysis_path}")
        file_analysis_list = load_json_from_server(server_analysis_path)

        for file_info in file_analysis_list:
            if file_info.get('file_path'):
                key_files_dict[file_info.get('file_path')] = file_info

        file_core_content = ""
        if hasattr(task_input, 'key_files') and task_input.key_files:
            message += "Key Files:\n"
            for i, file_ in enumerate(task_input.key_files, 1):
                file_path = file_.get('file_path')
                if file_path in key_files_dict:
                    file_info = key_files_dict[file_path]
                    doc_time = file_info.get('doc_time', 'Not specified')
                    source_authority = file_info.get('source_authority', 'Not assessed')
                    task_relevance = file_info.get('task_relevance', 'Not assessed')
                    information_richness = file_info.get('information_richness', 'Not assessed')
                    message += f"{i}. File: {file_path}\n"

                    file_core_content += f"[{str(i)}]doc_time:{doc_time}|||source_authority:{source_authority}|||task_relevance:{task_relevance}|||information_richness:{information_richness}|||summary_content:{file_info.get('core_content', '')}\n"
            message += "\n"
            message += f"file_core_content: {file_core_content}\n"
        else:
            message += "Key Files: None provided\n"

        message += "\n"
        # Add user query
        if hasattr(task_input, 'user_query') and task_input.user_query:
            message += f"User Query: {task_input.user_query}\n"
        else:
            message += "User Query: Not provided\n"

        return message

    def execute_task(self, task_input: WriterAgentTaskInput) -> AgentResponse:
        """
        Execute a writing task using ReAct pattern

        Args:
            task_input: TaskInput object with standardized task information

        Returns:
            AgentResponse with writing results and process trace
        """
        start_time = time.time()

        try:
            self.logger.info(f"Starting writing task: {task_input.task_content}")

            # Reset trace for new task
            self.reset_trace()

            # Initialize conversation history
            conversation_history = []

            # Build system prompt for writing
            system_prompt = self._build_system_prompt()

            # Build initial user message from TaskInput
            user_message = self._build_initial_message_from_task_input(task_input)

            # Add to conversation
            conversation_history.append({"role": "system", "content": system_prompt})
            conversation_history.append({"role": "user", "content": user_message + " /no_think"})

            iteration = 0
            task_completed = False

            self.logger.debug("Checking conversation history before model call")
            self.logger.debug(f"Conversation history: {conversation_history}")
            # ReAct Loop for Writing: Research → Plan → Write → Refine → Complete
            # Get model configuration from config
            from config.config import get_config
            config = get_config()
            model_config = config.get_custom_llm_config()

            pangu_url = model_config.get('url') or os.getenv('MODEL_REQUEST_URL', '')
            headers = llm_client.get_headers(model_config)
            openai_tools = None
            if llm_client.is_deepseek_api(model_config):
                schemas = self.get_tool_schemas_for_prompt()
                openai_tools = llm_client.mcp_schemas_to_openai_tools(schemas, list(self.available_tools.keys()))

            while iteration < self.config.max_iterations and not task_completed:
                # Check for cancellation at the start of each iteration
                if self._check_cancellation():
                    self.logger.info(f"WriterAgent task cancelled at iteration {iteration}")
                    execution_time = time.time() - start_time
                    return self.create_response(
                        success=False,
                        result="Task was cancelled by user",
                        iterations=iteration,
                        execution_time=execution_time
                    )

                iteration += 1
                self.logger.info(f"Writing iteration {iteration}")

                try:
                    # Get LLM response (reasoning + potential tool calls) with retry

                    max_retries = 10
                    response = None

                    for attempt in range(max_retries):
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
                            break  # Success, exit retry loop
                        except Exception as e:
                            self.logger.warning(f"LLM API call attempt {attempt + 1} failed: {e}")
                            if attempt == max_retries - 1:
                                raise e
                            time.sleep(6)

                    if response is None:
                        raise Exception("Failed to get response after all retries")

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
                        self.logger.debug(f"Arguments is string: {isinstance(arguments, str)}")

                        if tool_call.get("name") in ["writer_subjective_task_done"]:
                            task_completed = True
                            self.log_action(iteration, tool_call["name"], arguments, arguments)
                            tool_results.append(arguments)
                            break
                        if tool_call.get("name") in ["think"]:
                            tool_result = {
                                "tool_results": "You can proceed to invoke other tools if needed. But the next step cannot call the reflect tool"}
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
                            "Continue your writing process. If you need to research more, use available tools. "
                            "If you need to write or edit content, use file operations. "
                            "If your writing is complete and meets requirements, call writer_subjective_task_done. /no_think"
                        )
                        conversation_history.append({"role": "user", "content": followup_prompt})

                except Exception as e:
                    error_msg = f"Error in writing iteration {iteration}: {e}"
                    self.log_error(iteration, error_msg)
                    break

            execution_time = time.time() - start_time
            # Extract final result
            if task_completed:
                # Find the completion result in the trace
                completion_result = None
                for step in reversed(self.reasoning_trace):
                    if step.get("type") == "action" and step.get("tool") in ["writer_subjective_task_done"]:
                        completion_result = step.get("result")
                        break
                return self.create_response(
                    success=True,
                    result=completion_result,
                    iterations=iteration,
                    execution_time=execution_time
                )
            else:

                return self.create_response(
                    success=False,
                    error=f"Writing task not completed within {self.config.max_iterations} iterations",
                    iterations=iteration,
                    execution_time=execution_time
                )

        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            self.logger.error(f"Error in execute_react_loop: {e}")

            return self.create_response(
                success=False,
                error=str(e),
                iterations=iteration if 'iteration' in locals() else 0,
                execution_time=execution_time
            )


# Factory function for creating the writer agent
def create_writer_agent(
        model: Any = None,
        max_iterations: int = 15,  # More iterations for writing tasks
        temperature: Any = None,  # Resolved from env if not provided
        max_tokens: Any = None,
        shared_mcp_client=None
) -> WriterAgent:
    """
    Create a WriterAgent instance with server-managed sessions.
    
    Args:
        model: The LLM model to use
        max_iterations: Maximum number of iterations for writing tasks
        temperature: Temperature setting for creativity
        max_tokens: Maximum tokens for the AI response
        shared_mcp_client: Optional shared MCP client from parent agent (prevents extra sessions)

    Returns:
        Configured WriterAgent instance with writing-focused tools
    """
    # Import the enhanced config function
    from .base_agent import create_agent_config

    # Create agent configuration (session managed by MCP server)
    config = create_agent_config(
        agent_name="WriterAgent",
        model=model,
        max_iterations=max_iterations,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Create agent instance with shared MCP client (filtered tools for writing)
    agent = WriterAgent(config=config, shared_mcp_client=shared_mcp_client)

    return agent
