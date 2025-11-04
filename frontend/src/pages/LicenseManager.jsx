import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import axios from "axios";
import { toast } from "sonner";
import { Users, DollarSign, CheckCircle, XCircle, Calendar, TrendingUp } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const LicenseManager = () => {
  const [eas, setEas] = useState([]);
  const [selectedEA, setSelectedEA] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);

  const [assignForm, setAssignForm] = useState({
    customer_name: "",
    customer_email: "",
    expiration_date: "",
    purchase_amount: ""
  });

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
  });

  useEffect(() => {
    fetchEAs();
  }, []);

  useEffect(() => {
    if (selectedEA) {
      fetchAnalytics(selectedEA);
    }
  }, [selectedEA]);

  const fetchEAs = async () => {
    try {
      const response = await axios.get(`${API}/ea/list`, getAuthHeader());
      setEas(response.data);
      if (response.data.length > 0 && !selectedEA) {
        setSelectedEA(response.data[0].id);
      }
    } catch (error) {
      toast.error("Failed to fetch EAs");
    }
  };

  const fetchAnalytics = async (eaId) => {
    try {
      const response = await axios.get(`${API}/license/analytics/${eaId}`, getAuthHeader());
      setAnalytics(response.data);
    } catch (error) {
      console.error("Failed to fetch analytics", error);
      setAnalytics(null);
    }
  };

  const handleAssignLicense = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const ea = eas.find(e => e.id === selectedEA);
      const payload = {
        license_key: ea.license_key,
        customer_name: assignForm.customer_name,
        customer_email: assignForm.customer_email,
        expiration_date: assignForm.expiration_date || null,
        purchase_amount: assignForm.purchase_amount ? parseFloat(assignForm.purchase_amount) : null
      };

      await axios.post(`${API}/license/assign?ea_id=${selectedEA}`, payload, getAuthHeader());
      toast.success("License assigned successfully!");
      setAssignForm({ customer_name: "", customer_email: "", expiration_date: "", purchase_amount: "" });
      setAssignDialogOpen(false);
      fetchAnalytics(selectedEA);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to assign license");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "Never expires";
    return new Date(dateStr).toLocaleDateString();
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
  };

  return (
    <div className="space-y-6" data-testid="license-manager-page">
      {/* EA Selector */}
      <Card className="bg-white/10 backdrop-blur-xl border-white/20">
        <CardHeader>
          <CardTitle className="text-white">Select Expert Advisor</CardTitle>
          <CardDescription className="text-gray-300">Choose an EA to manage its licenses</CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={selectedEA} onValueChange={setSelectedEA}>
            <SelectTrigger data-testid="ea-selector" className="bg-white/5 border-white/20 text-white">
              <SelectValue placeholder="Select an EA" />
            </SelectTrigger>
            <SelectContent>
              {eas.map((ea) => (
                <SelectItem key={ea.id} value={ea.id}>
                  {ea.name} ({ea.type.toUpperCase()})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Analytics Cards */}
      {analytics && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Total Licenses */}
            <Card className="bg-white/10 backdrop-blur-xl border-white/20 hover:border-purple-500/50 transition-all">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-400">Total Licenses</p>
                    <p className="text-3xl font-bold text-white" data-testid="total-licenses">{analytics.total_licenses}</p>
                  </div>
                  <Users className="w-10 h-10 text-purple-400" />
                </div>
              </CardContent>
            </Card>

            {/* Active Licenses */}
            <Card className="bg-white/10 backdrop-blur-xl border-white/20 hover:border-green-500/50 transition-all">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-400">Active Licenses</p>
                    <p className="text-3xl font-bold text-green-400" data-testid="active-licenses">{analytics.active_licenses}</p>
                  </div>
                  <CheckCircle className="w-10 h-10 text-green-400" />
                </div>
              </CardContent>
            </Card>

            {/* Expired Licenses */}
            <Card className="bg-white/10 backdrop-blur-xl border-white/20 hover:border-red-500/50 transition-all">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-400">Expired</p>
                    <p className="text-3xl font-bold text-red-400" data-testid="expired-licenses">{analytics.expired_licenses}</p>
                  </div>
                  <XCircle className="w-10 h-10 text-red-400" />
                </div>
              </CardContent>
            </Card>

            {/* Total Revenue */}
            <Card className="bg-white/10 backdrop-blur-xl border-white/20 hover:border-blue-500/50 transition-all">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-400">Total Revenue</p>
                    <p className="text-3xl font-bold text-blue-400" data-testid="total-revenue">{formatCurrency(analytics.total_revenue)}</p>
                  </div>
                  <DollarSign className="w-10 h-10 text-blue-400" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Assign License Button */}
          <div className="flex justify-end">
            <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
              <DialogTrigger asChild>
                <Button 
                  data-testid="assign-license-btn"
                  className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                >
                  <Users className="w-4 h-4 mr-2" /> Assign New License
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-slate-900 border-white/20">
                <DialogHeader>
                  <DialogTitle className="text-white">Assign License</DialogTitle>
                  <DialogDescription className="text-gray-400">
                    Assign this EA's license to a customer
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleAssignLicense} className="space-y-4">
                  <div>
                    <Label className="text-gray-200">Customer Name</Label>
                    <Input
                      data-testid="customer-name-input"
                      type="text"
                      placeholder="John Doe"
                      value={assignForm.customer_name}
                      onChange={(e) => setAssignForm({ ...assignForm, customer_name: e.target.value })}
                      className="bg-white/5 border-white/20 text-white placeholder:text-gray-400"
                      required
                    />
                  </div>
                  <div>
                    <Label className="text-gray-200">Customer Email</Label>
                    <Input
                      data-testid="customer-email-input"
                      type="email"
                      placeholder="john@example.com"
                      value={assignForm.customer_email}
                      onChange={(e) => setAssignForm({ ...assignForm, customer_email: e.target.value })}
                      className="bg-white/5 border-white/20 text-white placeholder:text-gray-400"
                      required
                    />
                  </div>
                  <div>
                    <Label className="text-gray-200">Expiration Date (Optional)</Label>
                    <Input
                      data-testid="expiration-date-input"
                      type="date"
                      value={assignForm.expiration_date}
                      onChange={(e) => setAssignForm({ ...assignForm, expiration_date: e.target.value })}
                      className="bg-white/5 border-white/20 text-white"
                    />
                  </div>
                  <div>
                    <Label className="text-gray-200">Purchase Amount (Optional)</Label>
                    <Input
                      data-testid="purchase-amount-input"
                      type="number"
                      step="0.01"
                      placeholder="99.99"
                      value={assignForm.purchase_amount}
                      onChange={(e) => setAssignForm({ ...assignForm, purchase_amount: e.target.value })}
                      className="bg-white/5 border-white/20 text-white placeholder:text-gray-400"
                    />
                  </div>
                  <Button
                    data-testid="assign-submit-btn"
                    type="submit"
                    className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
                    disabled={loading}
                  >
                    {loading ? "Assigning..." : "Assign License"}
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          {/* License Table */}
          <Card className="bg-white/10 backdrop-blur-xl border-white/20">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <TrendingUp className="w-5 h-5" /> License Details
              </CardTitle>
              <CardDescription className="text-gray-300">All assigned licenses for {analytics.ea_name}</CardDescription>
            </CardHeader>
            <CardContent>
              {analytics.licenses.length === 0 ? (
                <div className="py-8 text-center">
                  <Users className="w-16 h-16 text-gray-500 mx-auto mb-4" />
                  <p className="text-gray-400" data-testid="no-licenses-message">No licenses assigned yet. Click "Assign New License" to get started.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="text-left text-gray-300 p-3">Customer</th>
                        <th className="text-left text-gray-300 p-3">Email</th>
                        <th className="text-left text-gray-300 p-3">Status</th>
                        <th className="text-left text-gray-300 p-3">Expiration</th>
                        <th className="text-left text-gray-300 p-3">Revenue</th>
                        <th className="text-left text-gray-300 p-3">Usage</th>
                        <th className="text-left text-gray-300 p-3">Last Used</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analytics.licenses.map((license) => (
                        <tr 
                          key={license.id} 
                          className="border-b border-white/5 hover:bg-white/5 transition-colors"
                          data-testid={`license-row-${license.id}`}
                        >
                          <td className="p-3 text-white">{license.customer_name}</td>
                          <td className="p-3 text-gray-300">{license.customer_email}</td>
                          <td className="p-3">
                            {license.is_active ? (
                              <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-500/20 text-green-400 rounded-full text-xs">
                                <CheckCircle className="w-3 h-3" /> Active
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-500/20 text-red-400 rounded-full text-xs">
                                <XCircle className="w-3 h-3" /> Expired
                              </span>
                            )}
                          </td>
                          <td className="p-3 text-gray-300 flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {formatDate(license.expiration_date)}
                          </td>
                          <td className="p-3 text-blue-400">{formatCurrency(license.purchase_amount || 0)}</td>
                          <td className="p-3 text-purple-400">{license.usage_count} times</td>
                          <td className="p-3 text-gray-400 text-sm">
                            {license.last_used ? new Date(license.last_used).toLocaleString() : "Never"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {!analytics && eas.length === 0 && (
        <Card className="bg-white/10 backdrop-blur-xl border-white/20">
          <CardContent className="py-16 text-center">
            <TrendingUp className="w-16 h-16 text-gray-500 mx-auto mb-4" />
            <p className="text-gray-400">No Expert Advisors found. Generate an EA first to manage licenses.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default LicenseManager;
