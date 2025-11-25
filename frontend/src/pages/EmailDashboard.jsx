import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import axios from "axios";
import { toast } from "sonner";
import { Mail, Send, RefreshCw, MessageSquare, CheckCircle, XCircle, Clock } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const EmailDashboard = () => {
  const [emails, setEmails] = useState([]);
  const [supportMessages, setSupportMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState(null);

  const [supportForm, setSupportForm] = useState({
    name: "",
    email: "",
    subject: "",
    message: ""
  });

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
  });

  useEffect(() => {
    fetchEmails();
    fetchSupportMessages();
  }, []);

  const fetchEmails = async () => {
    try {
      const response = await axios.get(`${API}/emails/all`, getAuthHeader());
      setEmails(response.data);
    } catch (error) {
      console.error("Failed to fetch emails", error);
    }
  };

  const fetchSupportMessages = async () => {
    try {
      const response = await axios.get(`${API}/support/messages`, getAuthHeader());
      setSupportMessages(response.data);
    } catch (error) {
      console.error("Failed to fetch support messages", error);
    }
  };

  const handleResendEmail = async (emailId) => {
    setLoading(true);
    try {
      await axios.post(`${API}/emails/resend/${emailId}`, {}, getAuthHeader());
      toast.success("Email resent successfully!");
      fetchEmails();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to resend email");
    } finally {
      setLoading(false);
    }
  };

  const handleSupportSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post(`${API}/support/message`, supportForm);
      toast.success("Support message sent successfully!");
      setSupportForm({ name: "", email: "", subject: "", message: "" });
      fetchSupportMessages();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send message");
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch(status) {
      case "sent":
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case "demo_sent":
        return <CheckCircle className="w-4 h-4 text-blue-400" />;
      case "failed":
        return <XCircle className="w-4 h-4 text-red-400" />;
      case "pending":
        return <Clock className="w-4 h-4 text-yellow-400" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusText = (status) => {
    switch(status) {
      case "sent":
        return "Sent";
      case "demo_sent":
        return "Demo (Logged)";
      case "failed":
        return "Failed";
      case "pending":
        return "Pending";
      default:
        return status;
    }
  };

  return (
    <div className="space-y-6" data-testid="email-dashboard-page">
      <Tabs defaultValue="emails" className="space-y-6">
        <TabsList className="bg-white/10 backdrop-blur-md border border-white/20">
          <TabsTrigger value="emails" data-testid="emails-tab">
            <Mail className="w-4 h-4 mr-2" /> Email Logs
          </TabsTrigger>
          <TabsTrigger value="support" data-testid="support-tab">
            <MessageSquare className="w-4 h-4 mr-2" /> Support
          </TabsTrigger>
        </TabsList>

        {/* Email Logs Tab */}
        <TabsContent value="emails">
          <Card className="bg-white/10 backdrop-blur-xl border-white/20">
            <CardHeader>
              <div className="flex justify-between items-center">
                <div>
                  <CardTitle className="text-2xl text-white flex items-center gap-2">
                    <Mail className="w-6 h-6 text-purple-400" />
                    Email Communication Logs
                  </CardTitle>
                  <CardDescription className="text-gray-300">
                    All emails sent from the system
                  </CardDescription>
                </div>
                <Button
                  onClick={fetchEmails}
                  variant="outline"
                  className="border-white/20 text-white hover:bg-white/10"
                  data-testid="refresh-emails-btn"
                >
                  <RefreshCw className="w-4 h-4 mr-2" /> Refresh
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {emails.length === 0 ? (
                <div className="py-16 text-center">
                  <Mail className="w-16 h-16 text-gray-500 mx-auto mb-4" />
                  <p className="text-gray-400" data-testid="no-emails-message">No emails sent yet</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="text-left text-gray-300 p-3">Status</th>
                        <th className="text-left text-gray-300 p-3">To</th>
                        <th className="text-left text-gray-300 p-3">Subject</th>
                        <th className="text-left text-gray-300 p-3">Type</th>
                        <th className="text-left text-gray-300 p-3">Sent At</th>
                        <th className="text-left text-gray-300 p-3">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {emails.map((email) => (
                        <tr 
                          key={email.id} 
                          className="border-b border-white/5 hover:bg-white/5 transition-colors"
                          data-testid={`email-row-${email.id}`}
                        >
                          <td className="p-3">
                            <div className="flex items-center gap-2">
                              {getStatusIcon(email.status)}
                              <span className="text-sm text-gray-300">{getStatusText(email.status)}</span>
                            </div>
                          </td>
                          <td className="p-3 text-white">{email.to_email}</td>
                          <td className="p-3 text-gray-300">{email.subject}</td>
                          <td className="p-3">
                            <span className="inline-block px-2 py-1 bg-purple-500/20 text-purple-300 rounded text-xs">
                              {email.email_type}
                            </span>
                          </td>
                          <td className="p-3 text-gray-400 text-sm">
                            {new Date(email.sent_at).toLocaleString()}
                          </td>
                          <td className="p-3">
                            <div className="flex gap-2">
                              <Dialog>
                                <DialogTrigger asChild>
                                  <Button
                                    data-testid={`view-email-btn-${email.id}`}
                                    variant="outline"
                                    size="sm"
                                    className="border-white/20 text-white hover:bg-white/10"
                                    onClick={() => setSelectedEmail(email)}
                                  >
                                    View
                                  </Button>
                                </DialogTrigger>
                                <DialogContent className="max-w-3xl bg-slate-900 border-white/20 max-h-[80vh] overflow-y-auto">
                                  <DialogHeader>
                                    <DialogTitle className="text-white">{selectedEmail?.subject}</DialogTitle>
                                    <DialogDescription className="text-gray-400">
                                      To: {selectedEmail?.to_email}
                                    </DialogDescription>
                                  </DialogHeader>
                                  <div 
                                    className="bg-white rounded-lg p-4"
                                    dangerouslySetInnerHTML={{ __html: selectedEmail?.body || "" }}
                                  />
                                </DialogContent>
                              </Dialog>

                              <Button
                                data-testid={`resend-email-btn-${email.id}`}
                                variant="outline"
                                size="sm"
                                className="border-green-500/50 text-green-400 hover:bg-green-500/10"
                                onClick={() => handleResendEmail(email.id)}
                                disabled={loading}
                              >
                                <RefreshCw className="w-3 h-3 mr-1" /> Resend
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Support Tab */}
        <TabsContent value="support">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Contact Form */}
            <Card className="bg-white/10 backdrop-blur-xl border-white/20">
              <CardHeader>
                <CardTitle className="text-2xl text-white flex items-center gap-2">
                  <Send className="w-6 h-6 text-blue-400" />
                  Contact Support
                </CardTitle>
                <CardDescription className="text-gray-300">
                  Send a message to support team
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSupportSubmit} className="space-y-4" data-testid="support-form">
                  <div>
                    <Label className="text-gray-200">Your Name</Label>
                    <Input
                      data-testid="support-name-input"
                      type="text"
                      placeholder="John Doe"
                      value={supportForm.name}
                      onChange={(e) => setSupportForm({ ...supportForm, name: e.target.value })}
                      className="bg-white/5 border-white/20 text-white placeholder:text-gray-400"
                      required
                    />
                  </div>
                  <div>
                    <Label className="text-gray-200">Your Email</Label>
                    <Input
                      data-testid="support-email-input"
                      type="email"
                      placeholder="john@example.com"
                      value={supportForm.email}
                      onChange={(e) => setSupportForm({ ...supportForm, email: e.target.value })}
                      className="bg-white/5 border-white/20 text-white placeholder:text-gray-400"
                      required
                    />
                  </div>
                  <div>
                    <Label className="text-gray-200">Subject</Label>
                    <Input
                      data-testid="support-subject-input"
                      type="text"
                      placeholder="How can we help?"
                      value={supportForm.subject}
                      onChange={(e) => setSupportForm({ ...supportForm, subject: e.target.value })}
                      className="bg-white/5 border-white/20 text-white placeholder:text-gray-400"
                      required
                    />
                  </div>
                  <div>
                    <Label className="text-gray-200">Message</Label>
                    <Textarea
                      data-testid="support-message-input"
                      placeholder="Please describe your issue or question..."
                      value={supportForm.message}
                      onChange={(e) => setSupportForm({ ...supportForm, message: e.target.value })}
                      className="bg-white/5 border-white/20 text-white placeholder:text-gray-400 min-h-[150px]"
                      required
                    />
                  </div>
                  <Button
                    data-testid="support-submit-btn"
                    type="submit"
                    className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700"
                    disabled={loading}
                  >
                    {loading ? "Sending..." : "Send Message"}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Support Messages */}
            <Card className="bg-white/10 backdrop-blur-xl border-white/20">
              <CardHeader>
                <CardTitle className="text-2xl text-white">Support Messages</CardTitle>
                <CardDescription className="text-gray-300">Recent support inquiries</CardDescription>
              </CardHeader>
              <CardContent>
                {supportMessages.length === 0 ? (
                  <div className="py-8 text-center">
                    <MessageSquare className="w-12 h-12 text-gray-500 mx-auto mb-3" />
                    <p className="text-gray-400" data-testid="no-support-messages">No support messages yet</p>
                  </div>
                ) : (
                  <div className="space-y-3 max-h-[500px] overflow-y-auto">
                    {supportMessages.map((msg) => (
                      <div
                        key={msg.id}
                        className="bg-white/5 rounded-lg p-4 border border-white/10"
                        data-testid={`support-msg-${msg.id}`}
                      >
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <p className="text-white font-semibold">{msg.name}</p>
                            <p className="text-gray-400 text-sm">{msg.email}</p>
                          </div>
                          <span className={`px-2 py-1 rounded text-xs ${
                            msg.status === 'new' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
                          }`}>
                            {msg.status}
                          </span>
                        </div>
                        <p className="text-purple-300 font-medium mb-2">{msg.subject}</p>
                        <p className="text-gray-300 text-sm mb-2">{msg.message}</p>
                        <p className="text-gray-500 text-xs">
                          {new Date(msg.created_at).toLocaleString()}
                        </p>
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
  );
};

export default EmailDashboard;
