# Copyright (c) 2025 Huawei Technologies Co., Ltd. All rights reserved.
# Copyright (c) 2026 South China Sea Institute of Oceanology, Chinese Academy of Sciences (SCSIO, CAS). All rights reserved.
"""
Planner Agent for Multi-Agent Task Coordination

This agent serves as a coordinator for complex tasks that require multiple agents
working together. It implements the ReAct pattern for reasoning and action.
"""
import time
import logging
import json
import requests
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
try:
    import litellm
except ImportError:
    litellm = None
from concurrent.futures import ThreadPoolExecutor, as_completed

# Base imports
from .base_agent import BaseAgent, AgentConfig, AgentResponse, WriterAgentTaskInput
# Import agent creators for built-in task assignment
from .writer_agent import create_writer_agent
from .. import llm_client
from .builtin_tool_schemas.planner_builtin_tool_schemas import get_builtin_assignment_schemas
from .prompt.planner_auto_prompt  import AUTO_SYSTEM_PROMPT_TEMPLATE
from .prompt.planner_writing_prompt  import WRITING_SYSTEM_PROMPT_TEMPLATE
from .prompt.planner_qa_prompt  import QA_SYSTEM_PROMPT_TEMPLATE
from .prompt.planner_sci_review_prompt import SCI_REVIEW_INTRO_SYSTEM_PROMPT_TEMPLATE
from .prompt.planner_writing_prompt_zh import WRITING_SYSTEM_PROMPT_TEMPLATE_ZH

class PlannerAgent(BaseAgent):
    """
    PlannerAgent coordinates multiple agents to handle complex user queries.
    
    The agent uses the ReAct pattern (Reasoning + Acting) to analyze user requests,
    break them down into manageable tasks, and coordinate the appropriate agents
    to complete the work.
    """

    def __init__(self, config: AgentConfig = None, shared_mcp_client=None, task_id: Optional[str] = None):
        # Set default agent name if not specified
        if config and not config.agent_name:
            config.agent_name = "PlannerAgent"
        elif not config:
            config = AgentConfig(agent_name="PlannerAgent")

        super().__init__(config, shared_mcp_client)

        # Planner-specific state
        self.execution_plan = []
        self.task_queue = []
		
		# Task management for cancellation support
        self.task_id = task_id
        self._cancellation_token = None
		
        # Add built-in task assignment methods to available tools
        self._add_builtin_assignment_tools()

        # Regenerate tool schemas with built-in assignment tools
        self.tool_schemas = self._build_tool_schemas()

        self.sub_agent_configs = {}

    def _add_builtin_assignment_tools(self):
        """Add built-in task assignment methods as available tools"""
        # Add assignment methods that share the MCP client connection
        self.available_tools.update({
            "assign_subjective_task_to_writer": self.assign_subjective_task_to_writer, # assign_subjective_task_to_writer
            "assign_multi_objective_tasks_to_info_seeker": self.assign_multi_objective_tasks_to_info_seeker,
            "assign_multi_subjective_tasks_to_info_seeker": self.assign_multi_subjective_tasks_to_info_seeker
        })
    def _build_system_prompt(self) -> str:
        """Build the system prompt for the planner agent"""
        tool_schemas_str = json.dumps(self.tool_schemas, ensure_ascii=False)

        auto_system_prompt_template = AUTO_SYSTEM_PROMPT_TEMPLATE
        writing_system_prompt_template = WRITING_SYSTEM_PROMPT_TEMPLATE
        qa_system_prompt_template = QA_SYSTEM_PROMPT_TEMPLATE

        planner_mode_system_prompt_map = {
            "auto": auto_system_prompt_template,
            "writing": WRITING_SYSTEM_PROMPT_TEMPLATE_ZH,
            "qa": qa_system_prompt_template
        }

        system_prompt = planner_mode_system_prompt_map[self.config.planner_mode]

        return system_prompt

    def assign_multi_objective_tasks_to_info_seeker(
            self,
            tasks: List[Dict[str, str]],
            max_workers: int = 8
        ) -> Dict[str, Any]:
        """
        Creates multiple TaskInput objects and routes them to info_seeker agents for concurrent execution.
        This tool enables the PlannerAgent to assign multiple research tasks through the MCP tool interface.
        
        Args:
            tasks: List of task dictionaries with the following keys:
                - task_content (required): The specific task content
                - task_steps_for_reference: Optional reference steps for execution
                - deliverable_contents: Format of expected deliverable
                - acceptance_checking_criteria: Criteria for task completion and quality
                - workspace_id: Workspace ID for stored files and memory
                - current_task_status: Description of current task status
                
            max_workers: Maximum concurrent threads (default=4)
            
        Returns:
            MCPToolResult with execution results for all tasks
        """
        try:
            # Validate task count (1-4 tasks)
            if not (1 <= len(tasks) <= 5):
                return {
                    "success": False,
                    "error": f"Invalid task count ({len(tasks)}). Must assign 1~5 tasks. Please re-plan the task execution schedule or re-decompose the task."
                }
            
            # Import here to avoid circular imports
            try:
                from agents import TaskInput, create_objective_information_seeker
            except ImportError:
                from ..agents import TaskInput, create_objective_information_seeker
            
            results = []
            import threading
            lock = threading.Lock()
            
            def process_task(task: Dict[str, str]):
                """Process a single task with thread-safe result collection"""
                try:
                    
                    
                    # Create TaskInput object
                    task_input = TaskInput(
                        task_content=task["task_content"],
                        task_steps_for_reference=task.get("task_steps_for_reference"),
                        deliverable_contents=task.get("deliverable_contents"),
                        current_task_status=task.get("current_task_status"),
                        workspace_id=None,  # Session/workspace is managed by the server; no need to set explicitly
                        acceptance_checking_criteria=task.get("acceptance_checking_criteria")
                    )
                    
                    # Create and execute with info seeker agent - use shared MCP client for session consistency
                    info_seeker_config = getattr(self, 'sub_agent_configs', {}).get('information_seeker', {})
                    info_seeker = create_objective_information_seeker(
                        model=info_seeker_config.get('model', self.config.model),
                        max_iterations=info_seeker_config.get('max_iterations', 30),
                        shared_mcp_client=self.mcp_tools.client if hasattr(self.mcp_tools, 'client') else self.mcp_tools
                    )

                    self.logger.info(f"Assigning task to InformationSeekerAgent: {task['task_content'][:8000]}...")

                    
                    # Execute the task
                    response = info_seeker.execute_task(task_input)

                    if response.success:
                        response_data = {
                            "task_content": task.get("task_content", "Unknown task"),
                            "success": True,
                            "data": response.result,
                            "agent_name": response.agent_name,
                            "iterations": response.iterations,
                            "execution_time": response.execution_time,
                            # "reasoning_trace": response.reasoning_trace
                        }
                    else:
                        response_data = {
                            "task_content": task.get("task_content", "Unknown task"),
                            "success": False,
                            "error": response.error,
                            "agent_name": response.agent_name
                        }                    
                    
                    # Thread-safe result collection
                    with lock:
                        results.append(response_data)
                    
                    return response_data
                    
                except Exception as e:
                    error_msg = f"Task processing failed: {str(e)}"
                    self.logger.error(error_msg)
                    with lock:
                        results.append({
                            "task_content": task.get("task_content", "Unknown task"),
                            "success": False,
                            "error": error_msg
                        })
                    return None
            
            # Execute tasks in parallel with thread pool
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_task, task) for task in tasks]
                # Wait for all tasks to complete
                for future in futures:
                    future.result()  # Raise exceptions if any
            
            # Check overall success
            all_success = all(task_result.get("success", False) for task_result in results)
            
            return {
                "success": all_success,
                "data": {"tasks": results},
                "error": None if all_success else "Some tasks failed",
                "metadata": {
                    "tool_name": "assign_multi_objective_tasks_to_info_seeker",
                    "task_count": len(tasks),
                    "success_count": sum(1 for r in results if r.get("success")),
                    "failure_count": sum(1 for r in results if not r.get("success"))
                }
            }
                
        except Exception as e:
            self.logger.error(f"Multi-task assignment failed: {e}")
            return {
                "success": False,
                "error": f"Multi-task assignment failed: {str(e)}"
            }
    

    def assign_multi_subjective_tasks_to_info_seeker(
            self,
            tasks: List[Dict[str, str]],
            max_workers: int = 8
    ) -> Dict[str, Any]:
        """
        Creates multiple TaskInput objects and routes them to info_seeker agents for concurrent execution.
        This tool enables the PlannerAgent to assign multiple research tasks through the MCP tool interface.
        
        Args:
            tasks: List of task dictionaries with the following keys:
                - task_content (required): The specific task content
                - task_steps_for_reference: Optional reference steps for execution
                - deliverable_contents: Format of expected deliverable
                - acceptance_checking_criteria: Criteria for task completion and quality
                - workspace_id: Workspace ID for stored files and memory
                - current_task_status: Description of current task status
                
            max_workers: Maximum concurrent threads (default=4)
            
        Returns:
            MCPToolResult with execution results for all tasks
        """
        try:
            # Validate task count (1-4 tasks)
            if not (1 <= len(tasks) <= 6):
                return {
                    "success": False,
                    "error": f"Invalid task count ({len(tasks)}). Must assign 1-6 tasks."
                }

            # Import here to avoid circular imports
            try:
                from agents import TaskInput, create_subjective_information_seeker
            except ImportError:
                from ..agents import TaskInput, create_subjective_information_seeker

            results = []
            import threading
            lock = threading.Lock()

            def process_task(task: Dict[str, str]):
                """Process a single task with thread-safe result collection"""
                try:
                    # Create TaskInput object
                    task_input = TaskInput(
                        task_content=task["task_content"],
                        task_steps_for_reference=task.get("task_steps_for_reference"),
                        deliverable_contents=task.get("deliverable_contents"),
                        current_task_status=task.get("current_task_status"),
                        workspace_id=self.get_session_info()["session_id"],  # Session/workspace is managed by the server; no need to set explicitly
                        acceptance_checking_criteria=task.get("acceptance_checking_criteria")
                    )

                    # Create and execute with info seeker agent - use shared MCP client for session consistency
                    info_seeker_config = getattr(self, 'sub_agent_configs', {}).get('information_seeker', {})
                    info_seeker = create_subjective_information_seeker(
                        model=info_seeker_config.get('model', self.config.model),
                        max_iterations=info_seeker_config.get('max_iterations', 30),
                        shared_mcp_client=self.mcp_tools.client if hasattr(self.mcp_tools, 'client') else self.mcp_tools
                    )

                    self.logger.info(f"Assigning task to InformationSeekerAgent: {task['task_content'][:8000]}...")

                    # Execute the task
                    response = info_seeker.execute_task(task_input)

                    if response.success:
                        response_data = {
                            "task_content": task.get("task_content", "Unknown task"),
                            "success": True,
                            "data": response.result,
                            "agent_name": response.agent_name,
                            "iterations": response.iterations,
                            "execution_time": response.execution_time,
                            # "reasoning_trace": response.reasoning_trace
                        }
                    else:
                        response_data = {
                            "task_content": task.get("task_content", "Unknown task"),
                            "success": False,
                            "error": response.error,
                            "agent_name": response.agent_name
                        }

                        # Thread-safe result collection
                    with lock:
                        results.append(response_data)

                    return response_data

                except Exception as e:
                    error_msg = f"Task processing failed: {str(e)}"
                    self.logger.error(error_msg)
                    with lock:
                        results.append({
                            "task_content": task.get("task_content", "Unknown task"),
                            "success": False,
                            "error": error_msg
                        })
                    return None

            # Execute tasks in parallel with thread pool
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_task, task) for task in tasks]
                # Wait for all tasks to complete
                for future in futures:
                    future.result()  # Raise exceptions if any

            # Check overall success
            all_success = all(task_result.get("success", False) for task_result in results)

            return {
                "success": all_success,
                "data": {"tasks": results},
                "error": None if all_success else "Some tasks failed",
                "metadata": {
                    "tool_name": "assign_multi_subjective_tasks_to_info_seeker",
                    "task_count": len(tasks),
                    "success_count": sum(1 for r in results if r.get("success")),
                    "failure_count": sum(1 for r in results if not r.get("success"))
                }
            }

        except Exception as e:
            self.logger.error(f"Multi-task assignment failed: {e}")
            return {
                "success": False,
                "error": f"Multi-task assignment failed: {str(e)}"
            }

    def assign_subjective_task_to_writer(
            self,
            task_content: str,
            user_query: str,
            key_files: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Assign a writing or content creation task to the WriterAgent

        Args:
            task_content: Detailed description of the writing task to be performed
            user_query: List storing previous information seeker subtask summaries intact to preserve information from each completed research task
            key_files: Curated list of relevant files with file_path and desc for each file

        Returns:
            Dictionary with task assignment results
        """
        try:

            self.logger.info("Assigning task to WriterAgent")

            # Create task input
            task_input = WriterAgentTaskInput(
                task_content=task_content,
                user_query=user_query,
                key_files=key_files,
                workspace_id=self.get_session_info()["session_id"],
            )

            # Create writer agent with shared MCP client and sub-agent configuration
            writer_config = getattr(self, 'sub_agent_configs', {}).get('writer', {})
            writer = create_writer_agent(
                shared_mcp_client=self.mcp_tools.client,
                model=writer_config.get('model', self.config.model),
                max_iterations=writer_config.get('max_iterations', 20),
                temperature=writer_config.get('temperature', 0.3),
                max_tokens=writer_config.get('max_tokens', 16384)
            )

            self.logger.info(f"Assigning task to WriterAgent: {task_content[:800]}...")

            # Execute the task with shared connection
            response = writer.execute_task(task_input)

            if response.success:
                return {
                    "success": True,
                    "data": response.result,
                    "agent_name": response.agent_name,
                    "iterations": response.iterations,
                    "execution_time": response.execution_time,
                    # "reasoning_trace": response.reasoning_trace
                }
            else:
                return {
                    "success": False,
                    "error": response.error,
                    "agent_name": response.agent_name
                }

        except Exception as e:
            self.logger.error(f"Failed to assign task to WriterAgent: {e}")
            return {
                "success": False,
                "error": f"Task assignment failed: {str(e)}"
            }

    def _build_agent_specific_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Build tool schemas for PlannerAgent using proper MCP architecture.
        Schemas come from MCP server via client, not direct imports.
        """

        # Get MCP tool schemas from server via client (proper MCP architecture)
        schemas = super()._build_agent_specific_tool_schemas()

        # Add schemas for built-in task assignment tools
        used_builtin_schemas = get_builtin_assignment_schemas(self.config.planner_mode)
        schemas.extend(used_builtin_schemas)

        return schemas

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
            self.logger.info(f"Task {self.task_id} cancellation detected")
            return True
        return False

    def _execute_react_loop(self, initial_message: str, max_iterations: int = 20) -> Dict[str, Any]:
        """
        Execute the ReAct loop for planning tasks

        Args:
            initial_message: Initial message to start the planning process
            max_iterations: Maximum number of iterations to perform

        Returns:
            Dictionary with execution results and trace
        """
        start_time = time.time()
        try:
            # Reset trace for new task
            self.reset_trace()
            # Initialize conversation history
            conversation_history = []

            # Build system prompt for planning
            system_prompt = self._build_system_prompt()
            self.logger.info(f"System prompt: {system_prompt}")
            # Add to conversation
            conversation_history.append({"role": "system", "content": system_prompt})
            conversation_history.append({"role": "user", "content": initial_message + " /no_think"})

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

            # Cap single-request timeout so one iteration cannot hang for hours (config may have 6000s)
            request_timeout = model_config.get("timeout", 6000)

            # ReAct Loop: Reasoning -> Acting -> Reasoning -> Acting...
            while iteration < self.config.max_iterations and not task_completed:
                iteration += 1
                self.logger.info(f"Planning iteration {iteration}")

                try:
                    # Get LLM response (reasoning + potential tool calls)
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
                                timeout=request_timeout
                            )
                            response = response.json()
                            self.logger.debug(f"API response received")
                            break
                        except Exception as e:
                            time.sleep(3)
                            retry_num += 1
                            if retry_num == max_retry_num:
                                self.logger.info(f"iteration {iteration} retry error: {str(e)}")
                                raise ValueError(str(e))
                            continue
                    assistant_message, tool_calls = llm_client.parse_chat_response(response, model_config)

                    self.logger.info(f"iteration {iteration} assistant_message: {assistant_message}")
                    self.logger.info(f"iteration {iteration} tool_calls: {str(tool_calls)}")

                    # Log the reasoning
                    reasoning_content = llm_client.extract_reasoning_from_content(assistant_message.get("content"))
                    if reasoning_content:
                        self.log_reasoning(iteration, reasoning_content)
                    if not assistant_message.get("content") and not tool_calls:
                        followup_prompt = "There is a problem with the format of model generation. Please try again."
                        conversation_history.append({"role": "user", "content": followup_prompt + " /no_think"})
                        continue

                    # Add assistant message to conversation (include tool_calls for OpenAI/DeepSeek)
                    conversation_history.append(assistant_message)

                    # Execute tool calls if any (Acting phase)
                    tool_results = []
                    for tool_call in tool_calls:
                        arguments = tool_call.get("arguments") or {}
                        if isinstance(arguments, str):
                            try:
                                arguments = json.loads(arguments) if arguments.strip() else {}
                            except json.JSONDecodeError:
                                arguments = {}
                        self.logger.debug(f"Arguments is string: {isinstance(arguments, str)}")

                        # Check if planning is complete
                        if tool_call.get("name") in ["planner_subjective_task_done", "planner_objective_task_done", "writer_subjective_task_done"]:
                            task_completed = True
                            self.log_action(iteration, tool_call["name"], arguments, arguments)
                            tool_results.append(arguments)
                            break
                        if tool_call.get("name") in ["think", "reflect"]:
                            tool_result = {"tool_results": "You can proceed to invoke other tools if needed. "}
                        else:
                            tool_result = self.execute_tool_call({"name": tool_call["name"], "arguments": arguments})

                        tool_results.append(tool_result)
                        self.log_action(iteration, tool_call["name"], arguments, tool_result)

                    n_executed = len(tool_results)
                    conversation_history.extend(
                        llm_client.build_tool_result_messages(tool_calls[:n_executed], tool_results, model_config, suffix=" /no_think")
                    )

                    # If no tool calls, encourage continued planning
                    if len(tool_calls) == 0:
                        # Add follow-up prompt to encourage action or completion
                        followup_prompt = (
                            "Continue your planning process. Use available tools to assign tasks to agents, "
                            "search for information, or coordinate work. When you have a complete answer, "
                            "call planner_subjective_task_done or planner_objective_task_done. /no_think"
                        )
                        conversation_history.append({"role": "user", "content": followup_prompt})

                except Exception as e:
                    error_msg = f"Error in planning iteration {iteration}: {e}"
                    self.log_error(iteration, error_msg)
                    break

            execution_time = time.time() - start_time

            # Extract final result
            if task_completed:
                # Find the completion result in the trace
                completion_result = None
                for step in reversed(self.reasoning_trace):
                    if step.get("type") == "action" and step.get("tool") in ["planner_subjective_task_done",
                                                                             "planner_objective_task_done"]:
                        completion_result = step.get("result")
                        break

                return {
                    "success": True,
                    "data": completion_result,
                    "reasoning_trace": self.reasoning_trace,
                    "iterations": iteration,
                    "execution_time": execution_time
                }
            else:
                return {
                    "success": False,
                    "error": f"Planning task not completed within {max_iterations} iterations",
                    "reasoning_trace": self.reasoning_trace,
                    "iterations": iteration,
                    "execution_time": execution_time
                }
        except Exception as e:
            execution_time = time.time() - start_time if 'start_time' in locals() else 0
            self.logger.error(f"Error in execute_react_loop: {e}")
            return {
                "success": False,
                "error": str(e),
                "reasoning_trace": self.reasoning_trace,
                "iterations": iteration if 'iteration' in locals() else 0,
                "execution_time": execution_time
            }


    def execute_task(self, user_query: str) -> AgentResponse:
        """
        Execute a planning task for the given user query

        Args:
            user_query: The user's query or request

        Returns:
            AgentResponse with planning results and process trace
        """
        start_time = time.time()

        try:
            self.logger.info(f"Starting planner task: {user_query}")

            # Execute the planning task using ReAct pattern
            result = self._execute_react_loop(
                initial_message=user_query,
                max_iterations=self.config.max_iterations  # Reasonable limit for planning tasks
            )

            execution_time = time.time() - start_time

            return AgentResponse(
                success=result.get("success", False),
                result=result.get("data"),
                error=result.get("error"),
                reasoning_trace=result.get("reasoning_trace", []),
                iterations=result.get("iterations", 0),
                execution_time=execution_time,
                agent_name=self.config.agent_name
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Planner execution failed: {e}")

            return AgentResponse(
                success=False,
                error=f"Planner execution failed: {str(e)}",
                reasoning_trace=[],
                iterations=0,
                execution_time=execution_time,
                agent_name=self.config.agent_name
            )


def create_planner_agent(
        model: Any = None,
        sub_agent_configs: Dict[str, Dict[str, Any]] = None,
        shared_mcp_client=None,
        **kwargs
) -> PlannerAgent:
    """
    Create a PlannerAgent instance with server-managed sessions.
    
    Args:
        model: The LLM model to use
        sub_agent_configs: Configuration for sub-agents (information_seeker, writer)
        shared_mcp_client: Optional shared MCP client to prevent duplicate connections
        **kwargs: Additional configuration options
        
    Returns:
        Configured PlannerAgent instance
    """
    # Import the enhanced config function
    from .base_agent import create_agent_config

    # Handle agent_name if provided in kwargs
    agent_name = kwargs.pop("agent_name", "PlannerAgent")
    
    # Handle task_id if provided in kwargs
    task_id = kwargs.pop("task_id", None)

    # Create agent configuration (session managed by MCP server)
    config = create_agent_config(
        agent_name=agent_name,
        model=model,
        **kwargs
    )

    # Create planner agent with optional shared MCP client
    planner = PlannerAgent(config=config, shared_mcp_client=shared_mcp_client, task_id=task_id)

    # Store sub-agent configurations for use when creating sub-agents
    planner.sub_agent_configs = sub_agent_configs or {
        "information_seeker": {},
        "writer": {}
    }

    return planner
