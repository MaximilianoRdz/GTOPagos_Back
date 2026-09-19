"""
GTOPagos Agent API Views
Expositor de endpoints REST y JSON-RPC para el Runtime de IA y el Servidor MCP.
"""
import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from agent.runtime.orchestrator import ai_orchestrator
from agent.mcp_server.server import mcp_server


class AgentChatView(APIView):
    """
    Endpoint para interacción directa con el Asistente Financiero GTOPagos.
    Procesa lenguaje natural, ejecuta skills matemáticas y devuelve widgets Generative UI.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="agent_chat",
        summary="Consulta al Asistente Financiero con Generative UI",
        description="Recibe una consulta en lenguaje natural, ejecuta herramientas MCP y responde con widgets interactivos.",
        request=inline_serializer(
            name="AgentChatRequest",
            fields={
                "query": serializers.CharField(required=True, help_text="Pregunta o instrucción financiera"),
                "context": serializers.DictField(required=False, default=dict, help_text="Contexto opcional del cliente")
            }
        ),
        responses={200: inline_serializer(
            name="AgentChatResponse",
            fields={
                "success": serializers.BooleanField(),
                "thought": serializers.CharField(),
                "action_type": serializers.CharField(),
                "data": serializers.DictField(),
                "user_message": serializers.CharField()
            }
        )}
    )
    def post(self, request):
        query = request.data.get("query", "")
        context = request.data.get("context", {})
        user = request.user if request.user.is_authenticated else None

        res = ai_orchestrator.process_query(query, user=user, context=context)
        return Response(res.model_dump(mode='json'), status=status.HTTP_200_OK)


class AgentMCPView(APIView):
    """
    Gateway JSON-RPC 2.0 para clientes MCP estándar (Model Context Protocol).
    Permite a Claude Desktop, Cursor o runtimes externos invocar Tools y Resources.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="agent_mcp_jsonrpc",
        summary="Gateway JSON-RPC 2.0 del Servidor MCP",
        description="Maneja solicitudes estándar de Model Context Protocol (tools/list, tools/call)."
    )
    def post(self, request):
        try:
            body = request.body.decode("utf-8")
            rpc_response_str = mcp_server.handle_json_rpc(body)
            rpc_response = json.loads(rpc_response_str)
            return Response(rpc_response, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"Internal JSON-RPC error: {str(e)}"}
            }, status=status.HTTP_400_BAD_REQUEST)


class AgentCapabilitiesView(APIView):
    """
    Devuelve la lista de herramientas, skills y capacidades disponibles en el Runtime.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="agent_capabilities",
        summary="Listado de Skills y Herramientas MCP",
        description="Devuelve el catálogo de herramientas financieras disponibles para el agente."
    )
    def get(self, request):
        tools = mcp_server.list_tools()
        return Response({
            "agent_name": ai_orchestrator.system_name,
            "version": ai_orchestrator.version,
            "tools_count": len(tools),
            "tools": tools,
            "architecture": "Spec-Driven Development (SDD) + MCP (Model Context Protocol)"
        }, status=status.HTTP_200_OK)
