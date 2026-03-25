# ================ MCP TOOL SCHEMAS ================

MCP_TOOL_SCHEMAS = {
    "think": {
        "name": "think",
        "description": "Use the tool to think about something. It will not obtain new information or make any changes to the repository, but just log the thought. Use it when complex reasoning or brainstorming is needed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "thought": {
                    "type": "string",
                    "description": "Your thoughts."
                }
            },
            "required": ["thought"]
        }
    },

    "reflect": {
        "name": "reflect",
        "description": "When multiple attempts yield no progress, use this tool to reflect on previous reasoning and planning, considering possible overlooked clues and exploring more possibilities. It will not obtain new information or make any changes to the repository.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reflect": {
                    "type": "string",
                    "description": "The specific content of your reflection"
                }
            },
            "required": ["reflect"]
        }
    },

    "batch_web_search": {
        "name": "batch_web_search",
        "description": "Search multiple queries using configurable search API with concurrent processing (no more than 8 search queries)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of search queries"
                },
                "max_results_per_query": {
                    "type": "integer",
                    "default": 4,
                    "description": "Maximum search results per query (limited to 10)"
                },
                "max_workers": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximum number of concurrent search requests"
                }
            },
            "required": ["queries"]
        }
    },

    "url_crawler": {
        "name": "url_crawler",
        "description": "Extract content from web pages using configurable URL crawler API. Input is a list of documents with metadata including URL and local file path for saving extracted content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "documents": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "Web page URL to extract content from"
                            },
                            "file_path": {
                                "type": "string",
                                "description": "Local path to save extracted full text content"
                            },
                            "title": {
                                "type": "string",
                                "description": "Title of the web page"
                            },
                            "time": {
                                "type": "string",
                                "description": "Publication time of the web page"
                            }
                        },
                        "required": ["url", "file_path"]
                    },
                    "description": "List of documents with metadata including URL and save path"
                },
                "max_tokens_per_url": {
                    "type": "integer",
                    "default": 4000,
                    "description": "Maximum tokens per URL result"
                },
                "include_metadata": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to include extraction metadata"
                },
                "max_workers": {
                    "type": "integer",
                    "default": 10,
                    "description": "Maximum number of concurrent extraction requests"
                }
            },
            "required": ["documents"]
        }
    },

    "concat_section_files": {
        "name": "concat_section_files",
        "description": "Concatenate the content of the saved section files into a single file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "final_file_path": {
                    "type": "string",
                    "description": "The final file path to save the concatenated content, save the file in the workspace **under the relative path `./report/`**, and specify the final_file_path as `./report/final_report.md`"
                },
                "section_files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Relative path to the saved section file"
                            }
                        },
                        "required": ["file_path"]
                    },
                    "description": "List of section files to concatenate"
                }
            },
            "required": ["section_files", "final_file_path"]
        }
    },

    # TODO 需要修改schame的格式，还是存在错误
    "search_result_classifier": {
        "name": "search_result_classifier",
        "description": "Intelligently classify and organize search result files according to a structured outline for comprehensive long-form content generation. Analyzes files across fouer key dimensions (document time, source authority, core content, and task relevance) and assigns relevant files to appropriate outline sections. Files may be assigned to multiple sections when their content spans different topics.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "outline": {
                    "type": "string",
                    "description": "The outline here must be consistent with the content and structure of the outline generated above"
                },
                "key_files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Relative path to the file containing research content"
                            }
                        },
                        "required": ["file_path"]
                    },
                    "description": "List of research files to be classified according to the outline"
                },
                "model": {
                    "type": "string",
                    "default": "pangu_auto",
                    "description": "AI model to use for classification and organization"
                },
                "temperature": {
                    "type": "number",
                    "default": 0.3,
                    "description": "Creativity level for the AI classification (0-1)"
                },
                "max_tokens": {
                    "type": "integer",
                    "default": 2000,
                    "description": "Maximum tokens for the AI response"
                }
            },
            "required": ["key_files", "outline"]
        }
    },

    "document_qa": {
        "name": "document_qa",
        "description": "Answer questions based on content stored in local files. Each file has a corresponding question. Reads files and uses an AI model to answer each question using the respective file content as context.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Relative path to the file (relative to workspace root)"
                            },
                            "question": {
                                "type": "string",
                                "description": "Question to ask about this file"
                            }
                        },
                        "required": ["file_path", "question"]
                    },
                    "description": "List of tasks, each containing a file path and a question"
                },
                "model": {
                    "type": "string",
                    "default": "gpt-4o-mini",
                    "description": "AI model to use for generating answers"
                },
                "temperature": {
                    "type": "number",
                    "default": 0.3,
                    "description": "Creativity level for the AI response (0-1)"
                },
                "max_tokens": {
                    "type": "integer",
                    "default": 2000,
                    "description": "Maximum tokens for the AI response"
                },
                "max_workers": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximum number of concurrent model API requests"
                }
            },
            "required": ["tasks"]
        }
    },

    "document_extract": {
        "name": "document_extract",
        "description": "Multi-dimensional analysis of locally stored files using AI models. Evaluates each file across four key dimensions: web page time extraction, source authority assessment, task relevance evaluation, and core content summarization (~300 words). Provides structured document analysis for research and content evaluation purposes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Relative path to the file (relative to workspace root)"
                            },
                            "task": {
                                "type": "string",
                                "description": "The content of the currently executed subtask"
                            }
                        },
                        "required": ["file_path", "task"]
                    },
                    "description": "List of tasks, each containing a file path and the current task"
                },
                "model": {
                    "type": "string",
                    "default": "pangu_auto",
                    "description": "AI model to use for generating answers"
                },
                "temperature": {
                    "type": "number",
                    "default": 0.3,
                    "description": "Creativity level for the AI response (0-1)"
                },
                "max_tokens": {
                    "type": "integer",
                    "default": 2000,
                    "description": "Maximum tokens for the AI response"
                },
                "max_workers": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximum number of concurrent model API requests"
                }
            },
            "required": ["tasks"]
        }
    },

    "section_writer": {
        "name": "section_writer",
        "description": "Write the current chapter content based on given web information and chapter structure; also consider user questions, completed chapters, and overall outline to ensure content relevance while avoiding duplication or contradictions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "written_chapters_summary": {
                    "type": "string",
                    "description": "The summary of the written chapters, including the content of the chapters and the reflections on the chapters. Note that this field should be concatenated with the summaries of all previously written chapters with '\\n', and do not modify the original summary. For example, if the current chapter is the third chapter, the value of this field is 'chapter 1 summary \\n chapter 2 summary'. If not, the value is set to 'No previous chapters written yet.'"
                },
                "task_content": {
                    "type": "string",
                    "description": "Detailed description of some requirements for writing the current chapter and avoidance prompts. If there are reflections from the `think` tool on previously written chapters, they can be added to this field."
                },
                "user_query": {
                    "type": "string",
                    "description": "The user query, ensure the drafted content is highly relevant to the user's inquiry."
                },
                "current_chapter_outline": {
                    "type": "string",
                    "description": "This field represents the current chapter structure to be drafted. When composing the chapter content, do not modify content and bold formatting symbols of the existing structure's titles!!!"
                },
                "overall_outline": {
                    "type": "string",
                    "description": "This field represents the overall outline of the article. When drafting the chapter content, you should consider the overall outline to ensure the chapter content is consistent with the overall outline."
                },
                "target_file_path": {
                    "type": "string",
                    "description": "The path to save the chapter content"
                },
                "key_files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Relative path to the file containing research content"
                            }
                        },
                        "required": ["file_path"]
                    },
                    "description": "These files are the source materials required for drafting the current chapter."
                },
                "model": {
                    "type": "string",
                    "default": "pangu_auto",
                    "description": "AI model to use for classification and organization"
                },
                "temperature": {
                    "type": "number",
                    "default": 0.3,
                    "description": "Creativity level for the AI classification (0-1)"
                },
                "max_tokens": {
                    "type": "integer",
                    "default": 5000,
                    "description": "Maximum tokens for the AI response"
                },
            },
            "required": ["user_query", "current_chapter_outline", "overall_outline", "target_file_path", "key_files"]
        }
    },

    "download_files": {
        "name": "download_files",
        "description": "Download files from URLs to the workspace",
        "inputSchema": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs to download"
                },
                "target_directory": {
                    "type": "string",
                    "description": "Directory to save files"
                },
                "overwrite": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to overwrite existing files"
                },
                "max_file_size_mb": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum file size in MB"
                }
            },
            "required": ["urls"]
        }
    },

    "process_user_uploaded_files": {
        "name": "process_user_uploaded_files",
        "description": "Process and download user-uploaded files from the Flask backend. This tool fetches files uploaded by users (e.g., PDFs, documents) and saves them to the workspace with high priority markers. Use this tool FIRST when user files are available to ensure they are analyzed before web search results.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file IDs from user uploads"
                },
                "backend_url": {
                    "type": "string",
                    "default": "http://localhost:5000",
                    "description": "Flask backend URL"
                }
            },
            "required": ["file_ids"]
        }
    },

    "process_library_files": {
        "name": "process_library_files",
        "description": "Process and download user-selected files from the document library. This tool fetches files that users have selected from their document library and saves them to the workspace. These files are treated equally with web search results - the LLM will judge their relevance and decide whether to cite them based on task_relevance, source_authority, and information_richness dimensions. Use this tool when users have selected specific files from their document library.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file IDs from document library"
                },
                "backend_url": {
                    "type": "string",
                    "default": "http://localhost:5000",
                    "description": "Flask backend URL"
                }
            },
            "required": ["file_ids"]
        }
    },

    "list_workspace": {
        "name": "list_workspace",
        "description": "List files and directories in the workspace",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Specify the directory path to list, using a relative path"
                },
                "recursive": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to list recursively"
                },
                "include_hidden": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to include hidden files"
                },
                "max_depth": {
                    "type": "integer",
                    "default": 3,
                    "description": "Maximum recursion depth"
                }
            },
            "required": []
        }
    },

    "str_replace_based_edit_tool": {
        "name": "str_replace_based_edit_tool",
        "description": "Create, view, and edit files with various operations",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "view", "str_replace", "insert", "append", "delete"],
                    "description": "Action to perform"
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to the file"
                },
                "content": {
                    "type": "string",
                    "description": "Content for create/insert/append actions"
                },
                "old_str": {
                    "type": "string",
                    "description": "String to replace (for str_replace)"
                },
                "new_str": {
                    "type": "string",
                    "description": "Replacement string (for str_replace)"
                },
                "line_number": {
                    "type": "integer",
                    "description": "Line number for insert action"
                }
            },
            "required": ["action", "file_path"]
        }
    },

    "file_read": {
        "name": "file_read",
        "description": "Read file content",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Relative path to the file (relative to workspace root)"
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "File encoding"
                }
            },
            "required": ["file_path"]
        }
    },

    "load_json": {
        "name": "load_json",
        "description": "Read json format file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Relative path to the file (relative to workspace root)"
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "File encoding"
                }
            },
            "required": ["file_path"]
        }
    },

    "file_write": {
        "name": "file_write",
        "description": "Write content to file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Relative path to the file (relative to workspace root)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write"
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "File encoding"
                },
                "create_dirs": {
                    "type": "boolean",
                    "default": True,
                    "description": "Create parent directories"
                }
            },
            "required": ["file_path", "content"]
        }
    },

    "file_grep_search": {
        "name": "file_grep_search",
        "description": "Search for pattern in files",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for"
                },
                "file_pattern": {
                    "type": "string",
                    "default": "*",
                    "description": "File pattern to search in"
                },
                "recursive": {
                    "type": "boolean",
                    "default": True,
                    "description": "Search recursively"
                },
                "ignore_case": {
                    "type": "boolean",
                    "default": False,
                    "description": "Ignore case in search"
                },
                "max_matches": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum number of matches"
                }
            },
            "required": ["pattern"]
        }
    },

    "file_find_by_name": {
        "name": "file_find_by_name",
        "description": "Find files by name pattern",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name_pattern": {
                    "type": "string",
                    "description": "Name pattern to search for"
                },
                "recursive": {
                    "type": "boolean",
                    "default": True,
                    "description": "Search recursively"
                },
                "case_sensitive": {
                    "type": "boolean",
                    "default": False,
                    "description": "Case sensitive search"
                },
                "max_results": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum number of results"
                }
            },
            "required": ["name_pattern"]
        }
    },

    "bash": {
        "name": "bash",
        "description": "Execute bash command in the workspace",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Bash command to execute"
                },
                "timeout": {
                    "type": "integer",
                    "default": 30,
                    "description": "Command timeout in seconds"
                },
                "capture_output": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to capture stdout/stderr"
                },
                "working_directory": {
                    "type": "string",
                    "description": "Working directory for command"
                }
            },
            "required": ["command"]
        }
    },

    "info_seeker_task_done": {
        "name": "info_seeker_task_done",
        "description": "Information Seeker Agent task completion reporting with information collection summary and related files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                # "save_analysis_file_path": {
                #     "type": "string",
                #     "description": "The path to save the analysis file, save the analysis file in the workspace **under the relative path `./doc_analysis/`**, and specify the file path as `/doc_analysis/file_analysis.jsonl`"
                # },
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
    },

    "section_writer_task_done": {
        "name": "section_writer_task_done",
        "description": "Section Writer Agent task completion reporting for chapter/section writing. Called when a chapter, section, or paragraph is completed to provide a brief overview of the written content and completion status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chapter_summary": {
                    "type": "string",
                    "description": "Brief summary of the content written in the current chapter/section, including main topics covered and key points addressed.",
                    "format": "markdown"
                },
                "key_topics_covered": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of main topics or themes addressed in the written chapter/section"
                },
                "completion_status": {
                    "type": "string",
                    "enum": ["completed", "partial", "failed"],
                    "description": "Final status of the chapter/section writing task"
                },
                "completion_analysis": {
                    "type": "string",
                    "description": "Brief analysis of the writing task completion including: assessment of content quality, evaluation of outline adherence, identification of any challenges encountered, and overall evaluation of the writing process success."
                }
            },
            "required": ["chapter_summary", "key_topics_covered", "completion_status", "completion_analysis"]
        }
    },

    "writer_task_done": {
        "name": "writer_task_done",
        "description": "Writer Agent task completion reporting for complete long-form content. Called after all chapters/sections are written to provide a summary of the complete long article, final completion status and analysis, and the storage path of the final consolidated article.",
        "inputSchema": {
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
            "required": ["final_article_path", "article_summary", "completion_status", "completion_analysis"]
        }
    },

    "semantic_search": {
        "name": "semantic_search",
        "description": "Search semantically through system-maintained knowledge index using OpenAI embeddings",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - can be natural language question or keywords"
                },
                "max_tokens": {
                    "type": "integer",
                    "default": 2000,
                    "description": "Maximum tokens to return in results (controls result size)"
                },
                "max_results": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximum number of results to return"
                },
                "similarity_threshold": {
                    "type": "number",
                    "default": 0.7,
                    "description": "Minimum similarity score (0-1) for results"
                },
                "filters": {
                    "type": "object",
                    "properties": {
                        "task_name": {
                            "type": "string",
                            "description": "Filter by specific task name"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Filter by files containing this path"
                        },
                        "is_final_output": {
                            "type": "boolean",
                            "description": "Filter by final output files only"
                        }
                    },
                    "description": "Optional filters to narrow search results"
                }
            },
            "required": ["query"]
        }
    },

    "knowledge_status": {
        "name": "knowledge_status",
        "description": "Get status and statistics about the system-managed knowledge index",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    "search_pubmed_key_words": {
        "name": "search_pubmed_key_words",
        "description": "Search for biological articles by keywords",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Search query string, only supports english"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 10)"
                }

            },
            "required": ["keywords"]
        }
    },

    "search_pubmed_advanced": {
        "name": "search_pubmed_advanced",
        "description": "Perform an advanced search for biological articles on PubMed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "term": {
                    "type": "string",
                    "description": "General search term, only supports english"
                },
                "title": {
                    "type": "string",
                    "description": "Search in title, only supports english"
                },
                "author": {
                    "type": "string",
                    "description": "Author name, only supports english"
                },
                "journal": {
                    "type": "string",
                    "description": "Journal name, only supports english"
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date for search range (format: YYYY/MM/DD)"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date for search range (format: YYYY/MM/DD)"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 10)"
                }
            },
            "required": []
        }
    },
    "get_pubmed_article": {
        "name": "get_pubmed_article",
        "description": "Obtain articles of biology on PubMed via PMID. Before calling this function, first use search_key_words or search_advanced to obtain the article's PMID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pmid": {
                    "type": "string",
                    "description": "PMID"
                }
            },
            "required": ["pmid"]
        }
    },
    "arxiv_search": {
        "name": "arxiv_search",
        "description": "Searcher for arXiv papers, return the metadata of papers. You can get paper_id with this function and then use it for reading paper.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string, only supports english"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max number of searched papers"
                },
            },
            "required": ["query"]
        }
    },
    "arxiv_read_paper": {
        "name": "arxiv_read_paper",
        "description": "Obtain Arxiv article content via paper_id. Before calling this function, first use arxiv_search to obtain the article's paper_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "paper_id": {
                    "type": "string",
                    "description": "arXiv paper ID"
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory where the PDF is/will be saved"
                }

            },
            "required": ["paper_id"]
        }
    },
    "medrxiv_search": {
        "name": "medrxiv_search",
        "description": "Searcher for biologically relevant papers, return the metadata of papers. You can get paper_id with this function and then use it for medrxiv_read_paper.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Category name to search for (e.g., \"cardiovascular medicine\"), only supports english"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max number of searched papers"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back for papers."
                }
            },
            "required": ["query"]
        }
    },
    "medrxiv_read_paper": {
        "name": "medrxiv_read_paper",
        "description": "Obtain medrxiv article content via paper_id. Before calling this function, first use medrxiv_search to obtain the article's paper_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "paper_id": {
                    "type": "string",
                    "description": "medrxiv paper ID"
                },
                "save_path": {
                    "type": "string",
                    "description": "Directory where the PDF is/will be saved"
                }

            },
            "required": ["paper_id"]
        }
    },
    "file_stats": {
        "name": "file_stats",
        "description": "Get comprehensive file statistics without reading full content - perfect for deciding reading strategy",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file (relative to workspace)"
                }
            },
            "required": ["file_path"]
        }
    },

    "file_read_lines": {
        "name": "file_read_lines",
        "description": "Read specific line ranges from a file without loading entire file - perfect for large files",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file"
                },
                "start_line": {
                    "type": "integer",
                    "default": 1,
                    "description": "Starting line number (1-based)"
                },
                "end_line": {
                    "type": "integer",
                    "description": "Ending line number (1-based, None for end of file)"
                },
                "max_lines": {
                    "type": "integer",
                    "default": 1000,
                    "description": "Maximum number of lines to read (safety limit)"
                }
            },
            "required": ["file_path"]
        }
    }

    # NOTE: Task assignment tool schemas removed - these are now built-in methods of PlannerAgent
    # to avoid circular dependency issues with sub-agents trying to create MCP client connections
}