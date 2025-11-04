import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import axios from "axios";
import { toast } from "sonner";
import { LogOut, Plus, Code2, Key, Activity, Download, Power, TrendingUp } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = ({ setIsAuthenticated }) => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [eas, setEas] = useState([]);
  const [mt5Accounts, setMt5Accounts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedEA, setSelectedEA] = useState(null);
  const [botStatuses, setBotStatuses] = useState({});

  const [generateForm, setGenerateForm] = useState({
    type: "ea",
    description: "",
    strategy_details: ""
  });

  const [mt5Form, setMt5Form] = useState({
    account_number: "",
    server: "",
    password: ""
  });

  useEffect(() => {
    const userData = localStorage.getItem("user");
    if (userData) {
      setUser(JSON.parse(userData));
      fetchEAs();
      fetchMT5Accounts();
    }
  }, []);

  useEffect(() => {
    if (eas.length > 0) {
      eas.forEach(ea => fetchBotStatus(ea.id));
    }
  }, [eas]);

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
  });

  const fetchEAs = async () => {
    try {
      const response = await axios.get(`${API}/ea/list`, getAuthHeader());
      setEas(response.data);
    } catch (error) {
      toast.error("Failed to fetch EAs");
    }
  };

  const fetchMT5Accounts = async () => {
    try {
      const response = await axios.get(`${API}/mt5/accounts`, getAuthHeader());
      setMt5Accounts(response.data);
    } catch (error) {
      toast.error("Failed to fetch MT5 accounts");
    }
  };

  const fetchBotStatus = async (eaId) => {
    try {
      const response = await axios.get(`${API}/bot/status/${eaId}`, getAuthHeader());
      setBotStatuses(prev => ({ ...prev, [eaId]: response.data.is_active }));
    } catch (error) {
      console.error("Failed to fetch bot status", error);
    }
  };

  const handleGenerateEA = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API}/ea/generate`, generateForm, getAuthHeader());
      toast.success(`${generateForm.type.toUpperCase()} generated successfully!`);
      setGenerateForm({ type: "ea", description: "", strategy_details: "" });
      fetchEAs();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to generate EA");
    } finally {
      setLoading(false);
    }
  };

  const handleConnectMT5 = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/mt5/connect`, mt5Form, getAuthHeader());
      toast.success("MT5 account connected successfully!");
      setMt5Form({ account_number: "", server: "", password: "" });
      fetchMT5Accounts();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to connect MT5 account");
    } finally {
      setLoading(false);
    }
  };

  const handleToggleBot = async (eaId, currentStatus) => {
    try {
      const response = await axios.post(
        `${API}/bot/toggle`,
        { ea_id: eaId, is_active: !currentStatus },
        getAuthHeader()
      );
      setBotStatuses(prev => ({ ...prev, [eaId]: response.data.is_active }));
      toast.success(`Bot ${response.data.is_active ? 'activated' : 'deactivated'}`);
    } catch (error) {
      toast.error("Failed to toggle bot status");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setIsAuthenticated(false);
    navigate("/");
  };

  const downloadCode = (ea) => {
    const element = document.createElement("a");
    const file = new Blob([ea.code], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = `${ea.name.replace(/\s+/g, '_')}.mq5`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="min-h-screen relative" data-testid="dashboard-page">
      {/* Background with Bull Image */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-purple-950 to-slate-900"></div>
        <div 
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `url('https://images.stockcake.com/public/c/6/1/c6169bb6-60f7-4572-b10a-6777972c9e08_large/futuristic-trading-dashboard-stockcake.jpg')`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundRepeat: 'no-repeat'
          }}
        ></div>
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent"></div>
      </div>

      {/* Content */}
      <div className="relative z-10">
        {/* Header */}
        <div className="border-b border-white/10 backdrop-blur-md bg-white/5">
          <div className="container mx-auto px-4 py-4 flex justify-between items-center">
            <div className="flex items-center gap-3">
              <TrendingUp className="w-8 h-8 text-purple-400" />
              <h1 className="text-2xl font-bold text-white">EA Generator</h1>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-gray-300" data-testid="user-name">Welcome, {user?.name}</span>
              <Button 
                data-testid="logout-btn"
                variant="outline" 
                onClick={handleLogout} 
                className="border-white/20 text-white hover:bg-white/10"
              >
                <LogOut className="w-4 h-4 mr-2" /> Logout
              </Button>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="container mx-auto px-4 py-8">
          <Tabs defaultValue="generate" className="space-y-6">
            <TabsList className="bg-white/10 backdrop-blur-md border border-white/20">
              <TabsTrigger value="generate" data-testid="generate-tab">Generate EA</TabsTrigger>
              <TabsTrigger value="my-eas" data-testid="my-eas-tab">My EAs</TabsTrigger>
              <TabsTrigger value="mt5" data-testid="mt5-tab">MT5 Accounts</TabsTrigger>
            </TabsList>

            {/* Generate EA Tab */}
            <TabsContent value="generate">
              <Card className="bg-white/10 backdrop-blur-xl border-white/20" data-testid="generate-ea-card">
                <CardHeader>
                  <CardTitle className="text-2xl text-white flex items-center gap-2">
                    <Code2 className="w-6 h-6 text-purple-400" />
                    Generate Expert Advisor or Indicator
                  </CardTitle>
                  <CardDescription className="text-gray-300">
                    Describe your trading strategy and let AI generate MQL5 code for you
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleGenerateEA} className="space-y-6">
                    <div>
                      <Label className="text-gray-200">Type</Label>
                      <Select
                        value={generateForm.type}
                        onValueChange={(value) => setGenerateForm({ ...generateForm, type: value })}
                      >
                        <SelectTrigger data-testid="type-select" className="bg-white/5 border-white/20 text-white">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="ea">Expert Advisor (EA)</SelectItem>
                          <SelectItem value="indicator">Indicator</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label className="text-gray-200">Strategy Description</Label>
                      <Textarea
                        data-testid="description-input"
                        placeholder="Describe your trading strategy (e.g., 'A scalping EA that buys when RSI is below 30 and sells when above 70')..."
                        value={generateForm.description}
                        onChange={(e) => setGenerateForm({ ...generateForm, description: e.target.value })}
                        className="bg-white/5 border-white/20 text-white placeholder:text-gray-400 min-h-[100px]"
                        required
                      />
                    </div>

                    <div>
                      <Label className="text-gray-200">Additional Strategy Details (Optional)</Label>
                      <Textarea
                        data-testid="strategy-details-input"
                        placeholder="Add more specific details like risk management, stop loss, take profit rules..."
                        value={generateForm.strategy_details}
                        onChange={(e) => setGenerateForm({ ...generateForm, strategy_details: e.target.value })}
                        className="bg-white/5 border-white/20 text-white placeholder:text-gray-400 min-h-[100px]"
                      />
                    </div>

                    <Button
                      data-testid="generate-submit-btn"
                      type="submit"
                      className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                      disabled={loading}
                    >
                      {loading ? (
                        <span className="flex items-center gap-2">
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          Generating...
                        </span>
                      ) : (
                        <span className="flex items-center gap-2">
                          <Plus className="w-4 h-4" /> Generate {generateForm.type.toUpperCase()}
                        </span>
                      )}
                    </Button>
                  </form>
                </CardContent>
              </Card>
            </TabsContent>

            {/* My EAs Tab */}
            <TabsContent value="my-eas">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {eas.length === 0 ? (
                  <Card className="col-span-full bg-white/10 backdrop-blur-xl border-white/20">
                    <CardContent className="py-16 text-center">
                      <Code2 className="w-16 h-16 text-gray-500 mx-auto mb-4" />
                      <p className="text-gray-400" data-testid="no-eas-message">No Expert Advisors generated yet. Create your first one!</p>
                    </CardContent>
                  </Card>
                ) : (
                  eas.map((ea) => (
                    <Card key={ea.id} className="bg-white/10 backdrop-blur-xl border-white/20 hover:border-purple-500/50 transition-all" data-testid={`ea-card-${ea.id}`}>
                      <CardHeader>
                        <div className="flex justify-between items-start">
                          <div>
                            <CardTitle className="text-xl text-white">{ea.name}</CardTitle>
                            <CardDescription className="text-gray-400">{ea.type.toUpperCase()}</CardDescription>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-400">Bot Status</span>
                            <Switch
                              data-testid={`bot-toggle-${ea.id}`}
                              checked={botStatuses[ea.id] || false}
                              onCheckedChange={() => handleToggleBot(ea.id, botStatuses[ea.id])}
                              className="data-[state=checked]:bg-green-500"
                            />
                            {botStatuses[ea.id] ? (
                              <Activity className="w-5 h-5 text-green-400 animate-pulse" />
                            ) : (
                              <Power className="w-5 h-5 text-gray-500" />
                            )}
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <p className="text-gray-300 text-sm">{ea.description}</p>
                        
                        <div className="bg-white/5 rounded-lg p-3 border border-white/10">
                          <div className="flex items-center gap-2 mb-1">
                            <Key className="w-4 h-4 text-purple-400" />
                            <span className="text-xs text-gray-400">License Key</span>
                          </div>
                          <code className="text-purple-300 text-xs break-all" data-testid={`license-key-${ea.id}`}>{ea.license_key}</code>
                        </div>

                        <div className="flex gap-2">
                          <Dialog>
                            <DialogTrigger asChild>
                              <Button 
                                data-testid={`view-code-btn-${ea.id}`}
                                variant="outline" 
                                className="flex-1 border-white/20 text-white hover:bg-white/10"
                                onClick={() => setSelectedEA(ea)}
                              >
                                <Code2 className="w-4 h-4 mr-2" /> View Code
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-4xl bg-slate-900 border-white/20 max-h-[80vh] overflow-y-auto">
                              <DialogHeader>
                                <DialogTitle className="text-white">{selectedEA?.name} - Code</DialogTitle>
                                <DialogDescription className="text-gray-400">MQL5 Code for your {selectedEA?.type}</DialogDescription>
                              </DialogHeader>
                              <div className="bg-black/50 rounded-lg p-4 overflow-x-auto">
                                <pre className="text-sm text-gray-300">
                                  <code>{selectedEA?.code}</code>
                                </pre>
                              </div>
                            </DialogContent>
                          </Dialog>

                          <Button
                            data-testid={`download-btn-${ea.id}`}
                            onClick={() => downloadCode(ea)}
                            className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                          >
                            <Download className="w-4 h-4 mr-2" /> Download
                          </Button>
                        </div>

                        <div className="text-xs text-gray-500">
                          Created: {new Date(ea.created_at).toLocaleDateString()}
                        </div>
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            </TabsContent>

            {/* MT5 Accounts Tab */}
            <TabsContent value="mt5">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Connect MT5 Form */}
                <Card className="bg-white/10 backdrop-blur-xl border-white/20">
                  <CardHeader>
                    <CardTitle className="text-2xl text-white">Connect MT5 Account</CardTitle>
                    <CardDescription className="text-gray-300">Add your MetaTrader 5 account credentials</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleConnectMT5} className="space-y-4" data-testid="mt5-connect-form">
                      <div>
                        <Label className="text-gray-200">Account Number</Label>
                        <Input
                          data-testid="mt5-account-input"
                          type="text"
                          placeholder="12345678"
                          value={mt5Form.account_number}
                          onChange={(e) => setMt5Form({ ...mt5Form, account_number: e.target.value })}
                          className="bg-white/5 border-white/20 text-white placeholder:text-gray-400"
                          required
                        />
                      </div>
                      <div>
                        <Label className="text-gray-200">Server</Label>
                        <Input
                          data-testid="mt5-server-input"
                          type="text"
                          placeholder="Broker-Server"
                          value={mt5Form.server}
                          onChange={(e) => setMt5Form({ ...mt5Form, server: e.target.value })}
                          className="bg-white/5 border-white/20 text-white placeholder:text-gray-400"
                          required
                        />
                      </div>
                      <div>
                        <Label className="text-gray-200">Password</Label>
                        <Input
                          data-testid="mt5-password-input"
                          type="password"
                          value={mt5Form.password}
                          onChange={(e) => setMt5Form({ ...mt5Form, password: e.target.value })}
                          className="bg-white/5 border-white/20 text-white"
                          required
                        />
                      </div>
                      <Button
                        data-testid="mt5-connect-btn"
                        type="submit"
                        className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                        disabled={loading}
                      >
                        {loading ? "Connecting..." : "Connect Account"}
                      </Button>
                    </form>
                  </CardContent>
                </Card>

                {/* Connected Accounts */}
                <Card className="bg-white/10 backdrop-blur-xl border-white/20">
                  <CardHeader>
                    <CardTitle className="text-2xl text-white">Connected Accounts</CardTitle>
                    <CardDescription className="text-gray-300">Your MT5 trading accounts</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {mt5Accounts.length === 0 ? (
                      <div className="py-8 text-center">
                        <p className="text-gray-400" data-testid="no-mt5-message">No MT5 accounts connected yet</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {mt5Accounts.map((account) => (
                          <div
                            key={account.id}
                            className="bg-white/5 rounded-lg p-4 border border-white/10"
                            data-testid={`mt5-account-${account.id}`}
                          >
                            <div className="flex justify-between items-center">
                              <div>
                                <p className="text-white font-semibold">Account: {account.account_number}</p>
                                <p className="text-gray-400 text-sm">Server: {account.server}</p>
                              </div>
                              <div className="flex items-center gap-2">
                                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                                <span className="text-green-400 text-sm">Connected</span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;