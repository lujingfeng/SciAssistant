from typing import List, Dict, Any


PLANNER_MODE_BUILTIN_TOOLS_MAP: Dict[str, List[str]] = {
    "auto": [
        "think",
        "reflect",
        "assign_multi_subjective_tasks_to_info_seeker",
        "assign_multi_objective_tasks_to_info_seeker",
        "assign_subjective_task_to_writer",
        "writer_subjective_task_done",
        "planner_subjective_task_done",
        "planner_objective_task_done",
    ],
    "writing": [
        "think",
        "reflect",
        "assign_multi_subjective_tasks_to_info_seeker",
        "assign_subjective_task_to_writer",
        "writer_subjective_task_done",
        "planner_subjective_task_done",
    ],
    "qa": [
        "think",
        "reflect",
        "assign_multi_objective_tasks_to_info_seeker",
        "planner_objective_task_done",
    ],
}


def get_builtin_assignment_schemas(planner_mode: str) -> List[Dict[str, Any]]:
    """
    Return builtin tool schemas filtered by planner mode.
    """
    builtin_assignment_schemas: List[Dict[str, Any]] = [
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
                            "description": "Your thoughts.",
                        }
                    },
                    "required": ["thought"],
                },
            },
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
                            "description": "The specific content of your reflection",
                        }
                    },
                    "required": ["reflect"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "assign_multi_subjective_tasks_to_info_seeker",
                "description": "Assign 1~6 research or information gathering tasks to different InformationSeekerAgents for parallel execution, each task descriptions must be semantically complete and clearly provide contextual information and potentially important reference documents.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "description": "List of tasks to be assigned to multiple InformationSeekerAgents",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "task_content": {
                                        "type": "string",
                                        "description": "Detailed description of the task to be performed",
                                    },
                                    "task_steps_for_reference": {
                                        "type": "string",
                                        "description": "Optional reference steps for task execution",
                                    },
                                    "deliverable_contents": {
                                        "type": "string",
                                        "description": "Expected format and content of deliverables",
                                    },
                                    "current_task_status": {
                                        "type": "string",
                                        "description": "Current status and context of the task, important documents that may be used and referenced",
                                    },
                                    "acceptance_checking_criteria": {
                                        "type": "string",
                                        "description": "Criteria for determining task completion and quality",
                                    },
                                },
                                "required": ["task_content"],
                            },
                        }
                    },
                    "required": ["tasks"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "assign_multi_objective_tasks_to_info_seeker",
                "description": "Assign 1~5 research or information gathering tasks to different InformationSeekerAgents for parallel execution, each task descriptions must be semantically complete and clearly provide contextual information and potentially important reference documents.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "description": "List of tasks to be assigned to multiple InformationSeekerAgents",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "task_content": {
                                        "type": "string",
                                        "description": "Detailed description of the task to be performed, the task description must be semantically complete",
                                    },
                                    "task_steps_for_reference": {
                                        "type": "string",
                                        "description": "Optional reference steps for task execution",
                                    },
                                    "deliverable_contents": {
                                        "type": "string",
                                        "description": "Expected format and content of deliverables",
                                    },
                                    "current_task_status": {
                                        "type": "string",
                                        "description": "Current status and context of the task, important documents that may be used and referenced",
                                    },
                                    "acceptance_checking_criteria": {
                                        "type": "string",
                                        "description": "Criteria for determining task completion and quality, and the requirements in the event of task completion failure",
                                    },
                                },
                                "required": ["task_content"],
                            },
                        }
                    },
                    "required": ["tasks"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "assign_subjective_task_to_writer",
                "description": "Assign a writing or content creation task to the WriterAgent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_query": {
                            "type": "string",
                            "description": "Pass in the original user question.",
                        },
                        "task_content": {
                            "type": "string",
                            "description": "Integrate and synthesize provided materials to generate comprehensive long-form content exceeding 10,000 words, especially careful not to give specific details, such as an outline plan, you are only providing the writer with a general description of the task.",
                        },
                        "key_files": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "file_path": {
                                        "type": "string",
                                        "description": "Relative path to the file containing research content",
                                    }
                                },
                                "required": ["file_path"],
                            },
                            "description": "Collect all key_files returned by the information seeker for long-form content creation.",
                        },
                    },
                    "required": ["user_query", "task_content", "key_files"],
                },
            },
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
                            "description": "The file path where the final article is saved.",
                        },
                        "article_summary": {
                            "type": "string",
                            "description": "Comprehensive summary of the complete long-form article, including main themes, key points covered, and overall narrative structure.",
                            "format": "markdown",
                        },
                        "completion_status": {
                            "type": "string",
                            "enum": ["completed", "partial", "failed"],
                            "description": "Final status of the complete long-form writing task",
                        },
                        "completion_analysis": {
                            "type": "string",
                            "description": "Analysis of the overall writing project completion including: assessment of article coherence and quality, evaluation of content organization and flow, identification of any challenges in the writing process, and overall evaluation of the long-form content creation success.",
                        },
                    },
                    "required": ["final_article_path", "article_summary", "completion_status", "completion_analysis"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "planner_subjective_task_done",
                "description": "When the writer agent is executed, the task done tool is called to end the planner's task.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "final_article_path": {
                            "type": "string",
                            "description": "The file path where the final article is saved.",
                        },
                        "task_summary": {
                            "type": "string",
                            "description": "This field is mainly used to describe the main content of the article, briefly summarize it, and finally indicate the path where the final article is saved.",
                            "format": "markdown",
                        },
                        "task_name": {
                            "type": "string",
                            "description": "The name of the task currently assigned to the agent, usually with underscores (e.g., 'web_research_ai_trends')",
                        },
                        "completion_status": {
                            "type": "string",
                            "enum": ["completed", "partial", "failed"],
                            "description": "Final task status",
                        },
                    },
                    "required": ["final_article_path", "task_summary", "task_name", "completion_status"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "planner_objective_task_done",
                "description": "Structured reporting of task completion details including summary, decisions, and final answer",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_summary": {
                            "type": "string",
                            "description": "Comprehensive markdown covering what the agent was asked to do, steps taken, tools used, key findings, files created, challenges",
                            "format": "markdown",
                        },
                        "task_name": {
                            "type": "string",
                            "description": "The name of the task currently assigned to the agent, usually with underscores (e.g., 'web_research_ai_trends')",
                        },
                        "key_files": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "file_path": {
                                        "type": "string",
                                        "description": "Relative path to created/modified file",
                                    },
                                    "desc": {
                                        "type": "string",
                                        "description": "File contents and creation purpose",
                                    },
                                    "is_final_output_file": {
                                        "type": "boolean",
                                        "description": "Whether file is primary deliverable",
                                    },
                                },
                                "required": ["file_path", "desc", "is_final_output_file"],
                            },
                            "description": "List of key files generated or modified during the task, with their details.",
                        },
                        "completion_status": {
                            "type": "string",
                            "enum": ["completed", "partial", "failed"],
                            "description": "Final task status",
                        },
                        "final_answer": {
                            "type": "string",
                            "description": "The final response displayed to the user",
                        },
                    },
                    "required": ["task_summary", "task_name", "key_files", "completion_status", "final_answer"],
                },
            },
        },
    ]

    allowed_tools = PLANNER_MODE_BUILTIN_TOOLS_MAP.get(
        planner_mode, PLANNER_MODE_BUILTIN_TOOLS_MAP["auto"]
    )
    return [
        schema
        for schema in builtin_assignment_schemas
        if schema["function"]["name"] in allowed_tools
    ]

