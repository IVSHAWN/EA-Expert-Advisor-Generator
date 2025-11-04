import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import axios from "axios";
import { toast } from "sonner";
import { TrendingUp, Zap, Shield, Code } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Landing = ({ setIsAuthenticated }) => {
  const navigate = useNavigate();
  const [showAuth, setShowAuth] = useState(false);
  const [loading, setLoading] = useState(false);

  const [registerData, setRegisterData] = useState({ name: "", email: "", password: "" });
  const [loginData, setLoginData] = useState({ email: "", password: "" });

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/register`, registerData);
      localStorage.setItem("token", response.data.access_token);
      localStorage.setItem("user", JSON.stringify(response.data.user));
      setIsAuthenticated(true);
      toast.success("Account created successfully!");
      navigate("/dashboard");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/login`, loginData);
      localStorage.setItem("token", response.data.access_token);
      localStorage.setItem("user", JSON.stringify(response.data.user));
      setIsAuthenticated(true);
      toast.success("Welcome back!");
      navigate("/dashboard");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-purple-950 to-slate-900">
        <div className="absolute inset-0 opacity-30">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500 rounded-full filter blur-[128px] animate-pulse"></div>
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500 rounded-full filter blur-[128px] animate-pulse" style={{ animationDelay: '1s' }}></div>
        </div>
      </div>

      {/* Content */}
      <div className="relative z-10">
        {!showAuth ? (
          // Hero Section
          <div className="container mx-auto px-4 py-20">
            <div className="max-w-6xl mx-auto text-center">
              {/* Hero Text */}
              <div className="mb-16 space-y-6">
                <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 leading-tight">
                  AI-Powered Expert Advisor Generator
                </h1>
                <p className="text-lg sm:text-xl text-gray-300 max-w-3xl mx-auto">
                  Transform your trading strategies into powerful MT5 Expert Advisors and Indicators with AI. No coding required.
                </p>
                <Button 
                  data-testid="get-started-btn"
                  onClick={() => setShowAuth(true)} 
                  size="lg" 
                  className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white px-8 py-6 text-lg rounded-full shadow-lg hover:shadow-purple-500/50 transition-all duration-300"
                >
                  Get Started <TrendingUp className="ml-2" />
                </Button>
              </div>

              {/* Features Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-20">
                <div className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10 hover:border-purple-500/50 transition-all duration-300">
                  <div className="bg-purple-600/20 w-14 h-14 rounded-xl flex items-center justify-center mb-4 mx-auto">
                    <Code className="w-7 h-7 text-purple-400" />
                  </div>
                  <h3 className="text-xl font-semibold mb-2">AI Code Generation</h3>
                  <p className="text-gray-400 text-sm">GPT-5 powered EA creation from your strategy description</p>
                </div>

                <div className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10 hover:border-blue-500/50 transition-all duration-300">
                  <div className="bg-blue-600/20 w-14 h-14 rounded-xl flex items-center justify-center mb-4 mx-auto">
                    <Shield className="w-7 h-7 text-blue-400" />
                  </div>
                  <h3 className="text-xl font-semibold mb-2">License Management</h3>
                  <p className="text-gray-400 text-sm">Secure license keys with subscription control</p>
                </div>

                <div className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10 hover:border-pink-500/50 transition-all duration-300">
                  <div className="bg-pink-600/20 w-14 h-14 rounded-xl flex items-center justify-center mb-4 mx-auto">
                    <Zap className="w-7 h-7 text-pink-400" />
                  </div>
                  <h3 className="text-xl font-semibold mb-2">MT5 Integration</h3>
                  <p className="text-gray-400 text-sm">Direct connection to MetaTrader 5 platform</p>
                </div>

                <div className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10 hover:border-cyan-500/50 transition-all duration-300">
                  <div className="bg-cyan-600/20 w-14 h-14 rounded-xl flex items-center justify-center mb-4 mx-auto">
                    <TrendingUp className="w-7 h-7 text-cyan-400" />
                  </div>
                  <h3 className="text-xl font-semibold mb-2">Bot Control</h3>
                  <p className="text-gray-400 text-sm">Activate/deactivate your EAs remotely</p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          // Auth Section
          <div className="container mx-auto px-4 py-12 flex items-center justify-center min-h-screen">
            <Card className="w-full max-w-md bg-white/10 backdrop-blur-xl border-white/20" data-testid="auth-card">
              <CardHeader>
                <CardTitle className="text-3xl font-bold text-center text-white">Welcome</CardTitle>
                <CardDescription className="text-center text-gray-300">Create an account or sign in to continue</CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="login" className="w-full">
                  <TabsList className="grid w-full grid-cols-2 bg-white/5">
                    <TabsTrigger value="login" data-testid="login-tab">Login</TabsTrigger>
                    <TabsTrigger value="register" data-testid="register-tab">Register</TabsTrigger>
                  </TabsList>

                  <TabsContent value="login">
                    <form onSubmit={handleLogin} className="space-y-4" data-testid="login-form">
                      <div>
                        <Label htmlFor="login-email" className="text-gray-200">Email</Label>
                        <Input
                          id="login-email"
                          data-testid="login-email-input"
                          type="email"
                          placeholder="trader@example.com"
                          value={loginData.email}
                          onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                          className="bg-white/5 border-white/20 text-white placeholder:text-gray-400"
                          required
                        />
                      </div>
                      <div>
                        <Label htmlFor="login-password" className="text-gray-200">Password</Label>
                        <Input
                          id="login-password"
                          data-testid="login-password-input"
                          type="password"
                          value={loginData.password}
                          onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                          className="bg-white/5 border-white/20 text-white"
                          required
                        />
                      </div>
                      <Button 
                        data-testid="login-submit-btn"
                        type="submit" 
                        className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700" 
                        disabled={loading}
                      >
                        {loading ? "Signing in..." : "Sign In"}
                      </Button>
                    </form>
                  </TabsContent>

                  <TabsContent value="register">
                    <form onSubmit={handleRegister} className="space-y-4" data-testid="register-form">
                      <div>
                        <Label htmlFor="register-name" className="text-gray-200">Name</Label>
                        <Input
                          id="register-name"
                          data-testid="register-name-input"
                          type="text"
                          placeholder="John Trader"
                          value={registerData.name}
                          onChange={(e) => setRegisterData({ ...registerData, name: e.target.value })}
                          className="bg-white/5 border-white/20 text-white placeholder:text-gray-400"
                          required
                        />
                      </div>
                      <div>
                        <Label htmlFor="register-email" className="text-gray-200">Email</Label>
                        <Input
                          id="register-email"
                          data-testid="register-email-input"
                          type="email"
                          placeholder="trader@example.com"
                          value={registerData.email}
                          onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                          className="bg-white/5 border-white/20 text-white placeholder:text-gray-400"
                          required
                        />
                      </div>
                      <div>
                        <Label htmlFor="register-password" className="text-gray-200">Password</Label>
                        <Input
                          id="register-password"
                          data-testid="register-password-input"
                          type="password"
                          value={registerData.password}
                          onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                          className="bg-white/5 border-white/20 text-white"
                          required
                        />
                      </div>
                      <Button 
                        data-testid="register-submit-btn"
                        type="submit" 
                        className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700" 
                        disabled={loading}
                      >
                        {loading ? "Creating account..." : "Create Account"}
                      </Button>
                    </form>
                  </TabsContent>
                </Tabs>

                <Button 
                  variant="ghost" 
                  onClick={() => setShowAuth(false)} 
                  className="w-full mt-4 text-gray-300 hover:text-white"
                  data-testid="back-to-home-btn"
                >
                  Back to Home
                </Button>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default Landing;