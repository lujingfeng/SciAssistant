# Copyright (c) 2026 South China Sea Institute of Oceanology, Chinese Academy of Sciences (SCSIO, CAS). All rights reserved.
"""
Unified LLM client for DeepSeek (OpenAI-compatible) and legacy Pangu-style APIs.
Ensures consistent model invocation and tool-calling across agents and mcp_tools.
"""
import json
import re
import os
from typing import Dict, Any, List, Optional, Tuple


def is_deepseek_api(model_config: Dict[str, Any]) -> bool:
    """Return True if the configured endpoint is DeepSeek (OpenAI-compatible)."""
    url = (model_config.get("url") or os.getenv("MODEL_REQUEST_URL") or "") or ""
    model = (model_config.get("model") or os.getenv("MODEL_NAME") or "") or ""
    return "deepseek.com" in url or "deepseek" in (model or "").lower()


def get_headers(model_config: Dict[str, Any]) -> Dict[str, str]:
    """
    Build request headers. For DeepSeek uses Authorization: Bearer <token>;
    for legacy uses csb-token.
    """
    token = model_config.get("token") or os.getenv("MODEL_REQUEST_TOKEN", "")
    headers = {"Content-Type": "application/json"}
    if is_deepseek_api(model_config):
        if token and not token.strip().lower().startswith("bearer "):
            token = f"Bearer {token.strip()}"
        headers["Authorization"] = token or "Bearer "
    else:
        headers["csb-token"] = token
    return headers


def build_chat_request(
    model_config: Dict[str, Any],
    messages: List[Dict[str, Any]],
    *,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build JSON body for POST /chat/completions.
    For DeepSeek: OpenAI-style (model, messages, temperature, max_tokens, optional tools).
    For legacy Pangu: chat_template + spaces_between_special_tokens.
    """
    model = model_config.get("model") or os.getenv("MODEL_NAME", "deepseek-chat")
    temperature = temperature if temperature is not None else model_config.get("temperature", 0.3)
    max_tokens = max_tokens if max_tokens is not None else model_config.get("max_tokens", 8192)

    if is_deepseek_api(model_config):
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = tools
            if tool_choice is not None:
                body["tool_choice"] = tool_choice
        return body

    # Legacy Pangu-style
    chat_template = (
        "{% for message in messages %}"
        "{% if loop.first and messages[0]['role'] != 'system' %}{{ '<s>[unused9]系统：[unused10]' }}{% endif %}"
        "{% if message['role'] == 'system' %}{{'<s>[unused9]系统：' + message['content'] + '[unused10]'}}{% endif %}"
        "{% if message['role'] == 'assistant' %}{{'[unused9]助手：' + message['content'] + '[unused10]'}}{% endif %}"
        "{% if message['role'] == 'tool' %}{{'[unused9]工具：' + message['content'] + '[unused10]'}}{% endif %}"
        "{% if message['role'] == 'function' %}{{'[unused9]方法：' + message['content'] + '[unused10]'}}{% endif %}"
        "{% if message['role'] == 'user' %}{{'[unused9]用户：' + message['content'] + '[unused10]'}}{% endif %}"
        "{% endfor %}{% if add_generation_prompt %}{{ '[unused9]助手：' }}{% endif %}"
    )
    return {
        "model": model,
        "chat_template": chat_template,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "spaces_between_special_tokens": False,
    }


def mcp_schemas_to_openai_tools(
    schemas: Any,
    tool_names_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Convert MCP tool schemas (dict or list) to OpenAI/DeepSeek tools list.
    If schemas is a dict (name -> {name, description, inputSchema}), convert each.
    If already a list of {type, function}, pass through (optionally filter).
    """
    openai_tools = []
    if isinstance(schemas, dict):
        for name, info in schemas.items():
            if tool_names_filter is not None and name not in tool_names_filter:
                continue
            if not isinstance(info, dict):
                continue
            params = info.get("inputSchema") or info.get("parameters") or {"type": "object", "properties": {}, "required": []}
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": info.get("name", name),
                    "description": info.get("description", f"Tool: {name}"),
                    "parameters": params,
                },
            })
    elif isinstance(schemas, list):
        for t in schemas:
            if not isinstance(t, dict):
                continue
            name = (t.get("function") or {}).get("name") or t.get("name")
            if tool_names_filter is not None and name not in tool_names_filter:
                continue
            if t.get("type") == "function" and t.get("function"):
                openai_tools.append(t)
            else:
                fn = t.get("function", t)
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": fn.get("name", "unknown"),
                        "description": fn.get("description", ""),
                        "parameters": fn.get("parameters") or fn.get("inputSchema") or {"type": "object", "properties": {}, "required": []},
                    },
                })
    return openai_tools


def parse_chat_response(
    response_json: Dict[str, Any],
    model_config: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Parse chat completion response into assistant message (for history) and list of tool calls.
    Returns (assistant_message, tool_calls).
    tool_calls: list of {"id", "name", "arguments"} for OpenAI-style; for legacy arguments may be str.
    """
    msg = response_json.get("choices", [{}])[0].get("message", {})
    content = msg.get("content") or ""
    tool_calls_raw = msg.get("tool_calls")

    if is_deepseek_api(model_config) and tool_calls_raw:
        tool_calls = []
        for tc in tool_calls_raw:
            fn = tc.get("function") or {}
            name = fn.get("name", "")
            args = fn.get("arguments", "{}")
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args.strip() else {}
                except json.JSONDecodeError:
                    args = {}
            tool_calls.append({
                "id": tc.get("id", ""),
                "name": name,
                "arguments": args,
            })
        # Assistant message for OpenAI must include tool_calls when present
        assistant_message = {"role": "assistant", "content": content or None}
        if tool_calls_raw:
            assistant_message["tool_calls"] = tool_calls_raw
        return assistant_message, tool_calls

    # Legacy: extract tool calls from content
    def extract_tool_calls_from_content(text):
        if not (text or isinstance(text, str)):
            return []
        tool_call_str = re.findall(r"\[unused11\]([\s\S]*?)\[unused12\]", text)
        if not tool_call_str:
            return []
        try:
            parsed = json.loads(tool_call_str[0].strip())
        except Exception:
            return []
        if isinstance(parsed, list):
            return [{"id": "", "name": t.get("name", ""), "arguments": t.get("arguments", {})} if isinstance(t, dict) else {"id": "", "name": "", "arguments": {}} for t in parsed]
        return []

    tool_calls = extract_tool_calls_from_content(content)
    assistant_message = {"role": "assistant", "content": content}
    return assistant_message, tool_calls


def build_tool_result_messages(
    tool_calls: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    model_config: Dict[str, Any],
    suffix: str = "",
) -> List[Dict[str, Any]]:
    """
    Build list of tool/role messages to append to conversation_history.
    For DeepSeek: one message per tool with role "tool", "content", "tool_call_id".
    For legacy: one message per tool with role "tool", "content" (no tool_call_id).
    """
    out = []
    for i, tc in enumerate(tool_calls):
        res = results[i] if i < len(results) else {}
        content = json.dumps(res, ensure_ascii=False, indent=2) + suffix
        if is_deepseek_api(model_config) and tc.get("id"):
            out.append({"role": "tool", "content": content, "tool_call_id": tc["id"]})
        else:
            out.append({"role": "tool", "content": content})
    return out


def extract_reasoning_from_content(content: Optional[str]) -> str:
    """Extract reasoning between [unused16] and [unused17] for logging; safe for None."""
    if not content:
        return ""
    try:
        part = content.split("[unused16]")[-1].split("[unused17]")[0]
        return part.strip() if part else ""
    except Exception:
        return ""
