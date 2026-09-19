from django.urls import path
from agent.views import AgentChatView, AgentMCPView, AgentCapabilitiesView, AgentExecuteActionView

urlpatterns = [
    path("chat/", AgentChatView.as_view(), name="agent-chat"),
    path("mcp/", AgentMCPView.as_view(), name="agent-mcp-gateway"),
    path("capabilities/", AgentCapabilitiesView.as_view(), name="agent-capabilities"),
    path("execute-action/", AgentExecuteActionView.as_view(), name="agent-execute-action"),
]
