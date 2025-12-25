import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Bot,
  Plus,
  MessageSquare,
  Clock,
  DollarSign,
  TrendingUp,
  Edit,
  Trash2,
  Play,
  Pause,
  PhoneIncoming,
  Mic,
  Volume2,
} from 'lucide-react';
import { api } from '@/services/api';
import { toast } from 'sonner';
import { format } from 'date-fns';

// Types
interface VoiceAgentConfig {
  id: string;
  name: string;
  description?: string;
  status: 'draft' | 'active' | 'inactive';
  system_prompt: string;
  greeting_message: string;
  fallback_message: string;
  goodbye_message: string;
  transfer_message: string;
  llm_model: string;
  tts_voice: string;
  max_turns: number;
  silence_timeout_seconds: number;
  max_call_duration_seconds: number;
  created_at: string;
  updated_at: string;
}

interface InboundRoute {
  id: string;
  did_pattern: string;
  description?: string;
  agent_config_id: string;
  is_active: boolean;
  priority: number;
  created_at: string;
}

interface VoiceAgentStats {
  total_conversations: number;
  total_duration_seconds: number;
  avg_duration_seconds: number;
  total_turns: number;
  avg_turns: number;
  resolution_breakdown: Record<string, number>;
  sentiment_breakdown: Record<string, number>;
  total_cost_usd: number;
  period_start: string;
  period_end: string;
}

interface Conversation {
  id: string;
  caller_number: string;
  call_duration_seconds: number;
  turn_count: number;
  resolution_status: string;
  sentiment?: string;
  started_at: string;
  estimated_cost_usd: number;
}

// API functions
const voiceAgentApi = {
  listAgents: async (): Promise<VoiceAgentConfig[]> => {
    const { data } = await api.get('/voice-agents');
    return data;
  },
  createAgent: async (data: Partial<VoiceAgentConfig>) => {
    const { data: result } = await api.post('/voice-agents', data);
    return result;
  },
  updateAgent: async ({ id, ...data }: { id: string } & Partial<VoiceAgentConfig>) => {
    const { data: result } = await api.put('/voice-agents/' + id, data);
    return result;
  },
  deleteAgent: async (id: string) => {
    await api.delete('/voice-agents/' + id);
  },
  activateAgent: async (id: string) => {
    const { data } = await api.post('/voice-agents/' + id + '/activate');
    return data;
  },
  deactivateAgent: async (id: string) => {
    const { data } = await api.post('/voice-agents/' + id + '/deactivate');
    return data;
  },
  listRoutes: async (): Promise<InboundRoute[]> => {
    const { data } = await api.get('/voice-agents/routes');
    return data;
  },
  createRoute: async (data: Partial<InboundRoute>) => {
    const { data: result } = await api.post('/voice-agents/routes', data);
    return result;
  },
  deleteRoute: async (id: string) => {
    await api.delete('/voice-agents/routes/' + id);
  },
  getStats: async (days = 7): Promise<VoiceAgentStats> => {
    const { data } = await api.get('/voice-agents/stats?days=' + days);
    return data;
  },
  listConversations: async (page = 1, pageSize = 20) => {
    const { data } = await api.get('/voice-agents/conversations?page=' + page + '&page_size=' + pageSize);
    return data;
  },
};

// TTS Voice options
const ttsVoices = [
  { value: 'alloy', label: 'Alloy (Neutral)' },
  { value: 'echo', label: 'Echo (Male)' },
  { value: 'fable', label: 'Fable (British)' },
  { value: 'onyx', label: 'Onyx (Deep Male)' },
  { value: 'nova', label: 'Nova (Female)' },
  { value: 'shimmer', label: 'Shimmer (Soft Female)' },
];

const llmModels = [
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini (Fast & Cheap)' },
  { value: 'gpt-4o', label: 'GPT-4o (Best Quality)' },
  { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
];

function StatsCards({ stats }: { stats: VoiceAgentStats | undefined }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Conversations</CardTitle>
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats?.total_conversations ?? 0}</div>
          <p className="text-xs text-muted-foreground">Last 7 days</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Avg Duration</CardTitle>
          <Clock className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {Math.round(stats?.avg_duration_seconds ?? 0)}s
          </div>
          <p className="text-xs text-muted-foreground">Per conversation</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Avg Turns</CardTitle>
          <TrendingUp className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{(stats?.avg_turns ?? 0).toFixed(1)}</div>
          <p className="text-xs text-muted-foreground">Exchanges per call</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
          <DollarSign className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">${(stats?.total_cost_usd ?? 0).toFixed(2)}</div>
          <p className="text-xs text-muted-foreground">OpenAI API costs</p>
        </CardContent>
      </Card>
    </div>
  );
}

function AgentConfigDialog({
  open,
  onOpenChange,
  agent,
  onSave,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agent?: VoiceAgentConfig;
  onSave: (data: Partial<VoiceAgentConfig>) => void;
}) {
  const [formData, setFormData] = useState<Partial<VoiceAgentConfig>>(
    agent ?? {
      name: '',
      description: '',
      system_prompt: 'You are a helpful customer service agent. Be concise, friendly, and helpful.',
      greeting_message: 'Hello, thank you for calling. How can I help you today?',
      fallback_message: "I'm sorry, I didn't understand that. Could you please repeat?",
      goodbye_message: 'Thank you for calling. Goodbye!',
      transfer_message: 'Please hold while I transfer you to an agent.',
      llm_model: 'gpt-4o-mini',
      tts_voice: 'nova',
      max_turns: 20,
      silence_timeout_seconds: 5,
      max_call_duration_seconds: 600,
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{agent ? 'Edit Voice Agent' : 'Create Voice Agent'}</DialogTitle>
          <DialogDescription>
            Configure your AI voice agent for handling inbound calls.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={formData.name ?? ''}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Customer Support Agent"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                value={formData.description ?? ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Handles general inquiries"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="system_prompt">System Prompt</Label>
            <Textarea
              id="system_prompt"
              value={formData.system_prompt ?? ''}
              onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
              placeholder="You are a helpful customer service agent..."
              rows={4}
              required
            />
            <p className="text-xs text-muted-foreground">
              Instructions for how the AI should behave. Be specific about tone, capabilities, and limitations.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="greeting_message">Greeting Message</Label>
              <Textarea
                id="greeting_message"
                value={formData.greeting_message ?? ''}
                onChange={(e) => setFormData({ ...formData, greeting_message: e.target.value })}
                rows={2}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="goodbye_message">Goodbye Message</Label>
              <Textarea
                id="goodbye_message"
                value={formData.goodbye_message ?? ''}
                onChange={(e) => setFormData({ ...formData, goodbye_message: e.target.value })}
                rows={2}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="llm_model">LLM Model</Label>
              <Select
                value={formData.llm_model}
                onValueChange={(value) => setFormData({ ...formData, llm_model: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select model" />
                </SelectTrigger>
                <SelectContent>
                  {llmModels.map((model) => (
                    <SelectItem key={model.value} value={model.value}>
                      {model.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="tts_voice">Voice</Label>
              <Select
                value={formData.tts_voice}
                onValueChange={(value) => setFormData({ ...formData, tts_voice: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select voice" />
                </SelectTrigger>
                <SelectContent>
                  {ttsVoices.map((voice) => (
                    <SelectItem key={voice.value} value={voice.value}>
                      {voice.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="max_turns">Max Turns</Label>
              <Input
                id="max_turns"
                type="number"
                value={formData.max_turns ?? 20}
                onChange={(e) => setFormData({ ...formData, max_turns: parseInt(e.target.value) })}
                min={1}
                max={100}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="silence_timeout">Silence Timeout (s)</Label>
              <Input
                id="silence_timeout"
                type="number"
                value={formData.silence_timeout_seconds ?? 5}
                onChange={(e) => setFormData({ ...formData, silence_timeout_seconds: parseFloat(e.target.value) })}
                min={1}
                max={30}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="max_duration">Max Duration (s)</Label>
              <Input
                id="max_duration"
                type="number"
                value={formData.max_call_duration_seconds ?? 600}
                onChange={(e) => setFormData({ ...formData, max_call_duration_seconds: parseInt(e.target.value) })}
                min={60}
                max={3600}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit">{agent ? 'Save Changes' : 'Create Agent'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function RouteDialog({
  open,
  onOpenChange,
  agents,
  onSave,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agents: VoiceAgentConfig[];
  onSave: (data: Partial<InboundRoute>) => void;
}) {
  const [formData, setFormData] = useState<Partial<InboundRoute>>({
    did_pattern: '',
    description: '',
    agent_config_id: '',
    is_active: true,
    priority: 100,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Inbound Route</DialogTitle>
          <DialogDescription>
            Map phone numbers to voice agents.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="did_pattern">DID Pattern</Label>
            <Input
              id="did_pattern"
              value={formData.did_pattern ?? ''}
              onChange={(e) => setFormData({ ...formData, did_pattern: e.target.value })}
              placeholder="+1555*"
              required
            />
            <p className="text-xs text-muted-foreground">
              Use * for wildcards. E.g., +1555* matches all numbers starting with +1555
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="agent">Voice Agent</Label>
            <Select
              value={formData.agent_config_id}
              onValueChange={(value) => setFormData({ ...formData, agent_config_id: value })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select agent" />
              </SelectTrigger>
              <SelectContent>
                {agents.map((agent) => (
                  <SelectItem key={agent.id} value={agent.id}>
                    {agent.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              value={formData.description ?? ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Main support line"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit">Create Route</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function VoiceAgentPage() {
  const queryClient = useQueryClient();
  const [showAgentDialog, setShowAgentDialog] = useState(false);
  const [showRouteDialog, setShowRouteDialog] = useState(false);
  const [editingAgent, setEditingAgent] = useState<VoiceAgentConfig | undefined>();

  // Queries
  const { data: agents = [], isLoading: agentsLoading } = useQuery({
    queryKey: ['voice-agents'],
    queryFn: voiceAgentApi.listAgents,
  });

  const { data: routes = [] } = useQuery({
    queryKey: ['voice-agent-routes'],
    queryFn: voiceAgentApi.listRoutes,
  });

  const { data: stats } = useQuery({
    queryKey: ['voice-agent-stats'],
    queryFn: () => voiceAgentApi.getStats(7),
  });

  const { data: conversationsData } = useQuery({
    queryKey: ['voice-agent-conversations'],
    queryFn: () => voiceAgentApi.listConversations(1, 10),
  });

  // Mutations
  const createAgentMutation = useMutation({
    mutationFn: voiceAgentApi.createAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voice-agents'] });
      toast.success('Voice agent created');
    },
    onError: () => toast.error('Failed to create agent'),
  });

  const updateAgentMutation = useMutation({
    mutationFn: voiceAgentApi.updateAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voice-agents'] });
      toast.success('Voice agent updated');
    },
    onError: () => toast.error('Failed to update agent'),
  });

  const deleteAgentMutation = useMutation({
    mutationFn: voiceAgentApi.deleteAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voice-agents'] });
      toast.success('Voice agent deleted');
    },
    onError: () => toast.error('Failed to delete agent'),
  });

  const activateMutation = useMutation({
    mutationFn: voiceAgentApi.activateAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voice-agents'] });
      toast.success('Voice agent activated');
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: voiceAgentApi.deactivateAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voice-agents'] });
      toast.success('Voice agent deactivated');
    },
  });

  const createRouteMutation = useMutation({
    mutationFn: voiceAgentApi.createRoute,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voice-agent-routes'] });
      toast.success('Route created');
    },
    onError: () => toast.error('Failed to create route'),
  });

  const deleteRouteMutation = useMutation({
    mutationFn: voiceAgentApi.deleteRoute,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voice-agent-routes'] });
      toast.success('Route deleted');
    },
  });

  const handleSaveAgent = (data: Partial<VoiceAgentConfig>) => {
    if (editingAgent) {
      updateAgentMutation.mutate({ id: editingAgent.id, ...data });
    } else {
      createAgentMutation.mutate(data);
    }
    setEditingAgent(undefined);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Bot className="h-8 w-8" />
            Voice Agent
          </h1>
          <p className="text-muted-foreground">
            AI-powered inbound call handling with OpenAI
          </p>
        </div>
        <Button onClick={() => setShowAgentDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Agent
        </Button>
      </div>

      {/* Stats */}
      <StatsCards stats={stats} />

      {/* Tabs */}
      <Tabs defaultValue="agents" className="space-y-4">
        <TabsList>
          <TabsTrigger value="agents" className="flex items-center gap-2">
            <Bot className="h-4 w-4" />
            Agents
          </TabsTrigger>
          <TabsTrigger value="routes" className="flex items-center gap-2">
            <PhoneIncoming className="h-4 w-4" />
            Inbound Routes
          </TabsTrigger>
          <TabsTrigger value="conversations" className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            Conversations
          </TabsTrigger>
        </TabsList>

        {/* Agents Tab */}
        <TabsContent value="agents" className="space-y-4">
          {agentsLoading ? (
            <Card>
              <CardContent className="py-10 text-center text-muted-foreground">
                Loading agents...
              </CardContent>
            </Card>
          ) : agents.length === 0 ? (
            <Card>
              <CardContent className="py-10 text-center">
                <Bot className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="font-semibold mb-2">No Voice Agents</h3>
                <p className="text-muted-foreground mb-4">
                  Create your first AI voice agent to handle inbound calls.
                </p>
                <Button onClick={() => setShowAgentDialog(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Agent
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {agents.map((agent) => (
                <Card key={agent.id}>
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <CardTitle className="flex items-center gap-2">
                          {agent.name}
                          <Badge
                            variant={agent.status === 'active' ? 'default' : 'secondary'}
                          >
                            {agent.status}
                          </Badge>
                        </CardTitle>
                        <CardDescription className="mt-1">
                          {agent.description || 'No description'}
                        </CardDescription>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Mic className="h-4 w-4" />
                        {agent.llm_model}
                      </span>
                      <span className="flex items-center gap-1">
                        <Volume2 className="h-4 w-4" />
                        {agent.tts_voice}
                      </span>
                    </div>
                    <div className="flex gap-2">
                      {agent.status === 'active' ? (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => deactivateMutation.mutate(agent.id)}
                        >
                          <Pause className="h-4 w-4 mr-1" />
                          Deactivate
                        </Button>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => activateMutation.mutate(agent.id)}
                        >
                          <Play className="h-4 w-4 mr-1" />
                          Activate
                        </Button>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setEditingAgent(agent);
                          setShowAgentDialog(true);
                        }}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          if (confirm('Delete this agent?')) {
                            deleteAgentMutation.mutate(agent.id);
                          }
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Routes Tab */}
        <TabsContent value="routes" className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => setShowRouteDialog(true)} disabled={agents.length === 0}>
              <Plus className="h-4 w-4 mr-2" />
              New Route
            </Button>
          </div>
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>DID Pattern</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {routes.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-muted-foreground py-10">
                      No inbound routes configured
                    </TableCell>
                  </TableRow>
                ) : (
                  routes.map((route) => (
                    <TableRow key={route.id}>
                      <TableCell className="font-mono">{route.did_pattern}</TableCell>
                      <TableCell>
                        {agents.find((a) => a.id === route.agent_config_id)?.name ?? 'Unknown'}
                      </TableCell>
                      <TableCell>{route.description || '-'}</TableCell>
                      <TableCell>
                        <Badge variant={route.is_active ? 'default' : 'secondary'}>
                          {route.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell>{route.priority}</TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            if (confirm('Delete this route?')) {
                              deleteRouteMutation.mutate(route.id);
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        {/* Conversations Tab */}
        <TabsContent value="conversations" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Conversations</CardTitle>
              <CardDescription>View AI conversation transcripts and analytics</CardDescription>
            </CardHeader>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Caller</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Turns</TableHead>
                  <TableHead>Resolution</TableHead>
                  <TableHead>Sentiment</TableHead>
                  <TableHead>Cost</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {!conversationsData?.items?.length ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-10">
                      No conversations yet
                    </TableCell>
                  </TableRow>
                ) : (
                  conversationsData.items.map((conv: Conversation) => (
                    <TableRow key={conv.id}>
                      <TableCell className="font-mono">{conv.caller_number}</TableCell>
                      <TableCell>{conv.call_duration_seconds}s</TableCell>
                      <TableCell>{conv.turn_count}</TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            conv.resolution_status === 'resolved'
                              ? 'default'
                              : conv.resolution_status === 'transferred'
                              ? 'secondary'
                              : 'destructive'
                          }
                        >
                          {conv.resolution_status}
                        </Badge>
                      </TableCell>
                      <TableCell>{conv.sentiment || '-'}</TableCell>
                      <TableCell>${conv.estimated_cost_usd.toFixed(4)}</TableCell>
                      <TableCell>{format(new Date(conv.started_at), 'MMM d, HH:mm')}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Dialogs */}
      <AgentConfigDialog
        open={showAgentDialog}
        onOpenChange={(open) => {
          setShowAgentDialog(open);
          if (!open) setEditingAgent(undefined);
        }}
        agent={editingAgent}
        onSave={handleSaveAgent}
      />
      <RouteDialog
        open={showRouteDialog}
        onOpenChange={setShowRouteDialog}
        agents={agents.filter((a) => a.status === 'active')}
        onSave={(data) => createRouteMutation.mutate(data)}
      />
    </div>
  );
}
