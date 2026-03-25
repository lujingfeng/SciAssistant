# Copyright (c) 2025 Huawei Technologies Co., Ltd. All rights reserved.
"""
Multi-Agent System Prompts
"""

from . import (
   planner_auto_prompt,
   planner_writing_prompt,
   planner_qa_prompt,
   planner_sci_review_prompt,
   objective_information_seeker_prompt,
   subjective_information_seeker_prompt,
   writer_prompt,
   objective_information_seeker_prompt_zh,
   subjective_information_seeker_prompt_zh,
   writer_prompt_zh,
)

__all__ = [
    # Base classes
    "planner_auto_prompt",
    "planner_writing_prompt",
    "planner_qa_prompt",
    "planner_sci_review_prompt",
    "objective_information_seeker_prompt",
    "subjective_information_seeker_prompt",
    "writer_prompt",
    "objective_information_seeker_prompt_zh",
    "subjective_information_seeker_prompt_zh",
    "writer_prompt_zh",
]

# Version info
__version__ = "0.1.0"
__author__ = "SCI Multi-Agent System"
