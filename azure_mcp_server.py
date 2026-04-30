#!/usr/bin/env python3
"""
Azure AI Foundry MCP Server - azure-ai-inference SDK ile
"""
import os
import sys
import json
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Azure AI Inference SDK importları
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage
from azure.core.credentials import AzureKeyCredential

# Sunucu tanımı
server = Server("azure-ai-foundry")

# Ortam değişkenleri
AZURE_ENDPOINT = os.getenv("AZURE_AI_ENDPOINT", "https://uniride-resource.services.ai.azure.com/models")
AZURE_API_KEY = os.getenv("AZURE_AI_API_KEY")
AZURE_API_VERSION = os.getenv("AZURE_AI_API_VERSION", "2025-01-01-preview")

def create_azure_client():
    """Azure ChatCompletionsClient oluştur"""
    if not AZURE_API_KEY:
        raise ValueError("AZURE_AI_API_KEY ortam değişkeni eksik!")
    
    return ChatCompletionsClient(
        endpoint=AZURE_ENDPOINT,
        credential=AzureKeyCredential(AZURE_API_KEY),
        api_version=AZURE_API_VERSION
    )

def parse_messages(messages_input):
    """
    MCP'den gelen messages'ı Azure SDK formatına çevir.
    Input: [{"role": "user", "content": "..."}, ...]
    Output: [UserMessage(...), SystemMessage(...), ...]
    """
    result = []
    for msg in messages_input:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "system":
            result.append(SystemMessage(content=content))
        elif role == "user":
            result.append(UserMessage(content=content))
        elif role == "assistant":
            result.append(AssistantMessage(content=content))
        else:
            # Bilinmeyen rolleri user olarak fallback yap
            result.append(UserMessage(content=content))
    
    return result

@server.list_tools()
async def list_tools():
    """MCP araçlarını listele"""
    return [
        Tool(
            name="azure_chat",
            description="Azure AI Foundry modelleri ile sohbet et (DeepSeek, Grok, GPT-5.4, Kimi vb.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string", 
                        "description": "Model adı (örn: DeepSeek-V3.2-Speciale-1)"
                    },
                    "prompt": {
                        "type": "string", 
                        "description": "Kullanıcı sorusu veya talimatı"
                    },
                    "messages": {
                        "type": "array",
                        "description": "Opsiyonel: Chat geçmişi [{role, content}, ...]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                                "content": {"type": "string"}
                            }
                        }
                    },
                    "temperature": {"type": "number", "default": 0.7, "minimum": 0, "maximum": 2},
                    "max_tokens": {"type": "integer", "default": 2048},
                    "top_p": {"type": "number", "default": 1.0},
                    "presence_penalty": {"type": "number", "default": 0.0},
                    "frequency_penalty": {"type": "number", "default": 0.0}
                },
                "required": ["model", "prompt"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Araç çağrısını işle"""
    if name == "azure_chat":
        try:
            # Client oluştur
            client = create_azure_client()
            
            # Mesajları hazırla
            messages_input = arguments.get("messages", [])
            # Prompt'ı son user message olarak ekle
            messages_input.append({"role": "user", "content": arguments.get("prompt")})
            messages = parse_messages(messages_input)
            
            # Parametreleri hazırla
            kwargs = {
                "messages": messages,
                "model": arguments.get("model"),
                "temperature": arguments.get("temperature", 0.7),
                "max_tokens": arguments.get("max_tokens", 2048),
                "top_p": arguments.get("top_p", 1.0),
                "presence_penalty": arguments.get("presence_penalty", 0.0),
                "frequency_penalty": arguments.get("frequency_penalty", 0.0)
            }
            
            # Azure SDK ile çağrı yap (sync call, async wrapper içinde)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: client.complete(**kwargs)
            )
            
            # Yanıtı parse et
            content = response.choices[0].message.content
            return [TextContent(type="text", text=content)]
            
        except Exception as e:
            error_msg = f"❌ Azure AI Hatası: {type(e).__name__}\n{str(e)}"
            # Detaylı hata için (güvenli şekilde)
            if hasattr(e, 'message') and e.message:
                error_msg += f"\nDetay: {e.message}"
            return [TextContent(type="text", text=error_msg)]
    
    raise ValueError(f"Bilinmeyen araç: {name}")

async def main():
    """Güncel MCP API ile çalıştırma"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, 
            write_stream, 
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())