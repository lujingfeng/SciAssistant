# Copyright (c) 2025 Huawei Technologies Co., Ltd. All rights reserved.
import json
from typing import Dict, Any, List
import time
import requests
import os
from .base_agent import BaseAgent, AgentConfig, AgentResponse, TaskInput
from .. import llm_client
from .prompt.subjective_information_seeker_prompt import SUBJECTIVE_INFORMATION_SEEKER_SYSTEM_PROMPT_TEMPLATE
from .prompt.subjective_information_seeker_prompt_zh import SUBJECTIVE_INFORMATION_SEEKER_SYSTEM_PROMPT_TEMPLATE_ZH

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

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the ReAct agent"""
        system_prompt_template = SUBJECTIVE_INFORMATION_SEEKER_SYSTEM_PROMPT_TEMPLATE_ZH
        return system_prompt_template

    @staticmethod
    def _build_initial_message_from_task_input(task_input: TaskInput) -> str:
        """Build the initial user message from TaskInput"""
        message = task_input.format_for_prompt()
        
        message += "\nPlease analyze this task and start your ReAct process:\n"
        message += "1. Reason about what information you need to gather\n"
        message += "2. Use appropriate tools to get that information\n"
        message += "3. Continue reasoning and acting until you have sufficient information\n"
        message += "4. Call info_seeker_subjective_task_done when ready to provide your complete findings\n\n"
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
            conversation_history.append({"role": "user", "content": user_message + " /no_think"})
            
            iteration = 0
            task_completed = False
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

            self.config.max_iterations = 30
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

                        if tool_call.get("name") in ["info_seeker_subjective_task_done"]:
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
                            "Continue your analysis. If you need more information, use available tools. "
                            "If you have enough information to answer the question, call info_seeker_subjective_task_done with your complete context."
                        )
                        conversation_history.append({"role": "user", "content": followup_prompt + " /no_think"})
                    if iteration == self.config.max_iterations-3:
                        followup_prompt = "Due to length and number of rounds restrictions, you must now call the `info_seeker_subjective_task_done` tool to report the completion of your task."
                        conversation_history.append({"role": "user", "content": followup_prompt + " /no_think"})
                    
                    
                except Exception as e:
                    error_msg = f"Error in planning iteration {iteration}: {e}"
                    self.log_error(iteration, error_msg)
                    break
            
            execution_time = time.time() - start_time
            # Extract final result
            if task_completed:
                # Find the task_done result in the trace
                task_done_result = None
                for step in reversed(self.reasoning_trace):
                    if step.get("type") == "action" and step.get("tool") == "info_seeker_subjective_task_done":
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
                    "name": "info_seeker_subjective_task_done",
                    "description": "Information Seeker Agent task completion reporting with information collection summary and related files.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_summary": {
                                "type": "string",
                                "description": "Simple summary of what information has been collected for the current task and what new discoveries have been made.",
                                "format": "markdown"
                            },
                            "key_files": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {
                                            "type": "string",
                                            "description": "Relative path to the file with collected content"
                                        },
                                    },
                                    "required": ["file_path"]
                                },
                                "description": "Collect files highly relevant to this task. "
                            },
                            "completion_status": {
                                "type": "string",
                                "enum": ["completed", "partial", "failed"],
                                "description": "Final status of the information gathering task"
                            },
                            "completion_analysis": {
                                "type": "string",
                                "description": "Brief analysis of task completion quality, information thoroughness, and any limitations or gaps."
                            }
                        },
                        "required": ["task_summary", "key_files", "completion_status", "completion_analysis"]
                    }
                }
            },
        ]

        schemas.extend(builtin_assignment_schemas)

        return schemas


# Factory function for creating the agent
def create_subjective_information_seeker(
    model: str = "pangu_auto",
    max_iterations: int = 10,
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
    from .base_agent import create_agent_config
    
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
