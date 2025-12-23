import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import axios from "axios";
import { toast } from "sonner";
import { Users, UserCheck, UserX, Shield, TrendingUp, DollarSign, Activity, Ban, Trash2, CheckCircle, XCircle, Clock } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdminPanel = () => {
  const [users, setUsers] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userActivity, setUserActivity] = useState(null);
  const [loading, setLoading] = useState(false);

  const getAuthHeader = () => ({
    headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
  });

  useEffect(() => {
    fetchUsers();
    fetchAnalytics();
  }, []);

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/admin/users`, getAuthHeader());
      setUsers(response.data);
    } catch (error) {
      toast.error("Failed to fetch users");
    }
  };

  const fetchAnalytics = async () => {
    try {
      const response = await axios.get(`${API}/admin/analytics`, getAuthHeader());
      setAnalytics(response.data);
    } catch (error) {
      toast.error("Failed to fetch analytics");
    }
  };

  const fetchUserActivity = async (userId) => {
    try {
      const response = await axios.get(`${API}/admin/user/${userId}/activity`, getAuthHeader());
      setUserActivity(response.data);
    } catch (error) {
      toast.error("Failed to fetch user activity");
    }
  };

  const handleApproveUser = async (userId) => {
    setLoading(true);
    try {
      await axios.put(`${API}/admin/users/${userId}/approve`, {}, getAuthHeader());
      toast.success("User approved successfully!");
      fetchUsers();
      fetchAnalytics();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to approve user");
    } finally {
      setLoading(false);
    }
  };

  const handleRejectUser = async (userId) => {
    setLoading(true);
    try {
      await axios.put(`${API}/admin/users/${userId}/reject`, {}, getAuthHeader());
      toast.success("User rejected and removed");
      fetchUsers();
      fetchAnalytics();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to reject user");
    } finally {
      setLoading(false);
    }
  };

  const handleSuspendUser = async (userId) => {
    setLoading(true);
    try {
      await axios.put(`${API}/admin/users/${userId}/suspend`, {}, getAuthHeader());
      toast.success("User suspended");
      fetchUsers();
      fetchAnalytics();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to suspend user");
    } finally {
      setLoading(false);
    }
  };

  const handleActivateUser = async (userId) => {
    setLoading(true);
    try {
      await axios.put(`${API}/admin/users/${userId}/activate`, {}, getAuthHeader());
      toast.success("User activated");
      fetchUsers();
      fetchAnalytics();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to activate user");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm("Are you sure? This will delete the user and ALL their data permanently!")) {
      return;
    }
    
    setLoading(true);
    try {
      await axios.delete(`${API}/admin/users/${userId}`, getAuthHeader());
      toast.success("User deleted");
      fetchUsers();
      fetchAnalytics();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete user");
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      pending: "bg-yellow-500/20 text-yellow-400",
      active: "bg-green-500/20 text-green-400",
      suspended: "bg-red-500/20 text-red-400"
    };
    
    const icons = {
      pending: <Clock className="w-3 h-3" />,
      active: <CheckCircle className="w-3 h-3" />,
      suspended: <XCircle className="w-3 h-3" />
    };
    
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 ${styles[status]} rounded-full text-xs`}>
        {icons[status]} {status}
      </span>
    );
  };

  const pendingUsers = users.filter(u => u.status === "pending");
  const activeUsers = users.filter(u => u.status === "active");
  const suspendedUsers = users.filter(u => u.status === "suspended");

  return (
    <div className="space-y-6" data-testid="admin-panel-page">
      {/* Analytics Cards */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="bg-white/10 backdrop-blur-xl border-white/20">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400">Total Users</p>
                  <p className="text-3xl font-bold text-white">{analytics.total_users}</p>
                </div>
                <Users className="w-10 h-10 text-purple-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white/10 backdrop-blur-xl border-white/20">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400">Pending Approval</p>
                  <p className="text-3xl font-bold text-yellow-400">{analytics.pending_users}</p>
                </div>
                <Clock className="w-10 h-10 text-yellow-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white/10 backdrop-blur-xl border-white/20">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400">Total EAs</p>
                  <p className="text-3xl font-bold text-blue-400">{analytics.total_eas}</p>
                </div>
                <TrendingUp className="w-10 h-10 text-blue-400" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white/10 backdrop-blur-xl border-white/20">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-400">Total Revenue</p>
                  <p className="text-3xl font-bold text-green-400">
                    ${analytics.total_revenue.toLocaleString('en-US', {minimumFractionDigits: 2})}
                  </p>
                </div>
                <DollarSign className="w-10 h-10 text-green-400" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* User Management Tabs */}
      <Tabs defaultValue="pending" className="space-y-6">
        <TabsList className="bg-white/10 backdrop-blur-md border border-white/20">
          <TabsTrigger value="pending">
            Pending ({pendingUsers.length})
          </TabsTrigger>
          <TabsTrigger value="active">
            Active ({activeUsers.length})
          </TabsTrigger>
          <TabsTrigger value="suspended">
            Suspended ({suspendedUsers.length})
          </TabsTrigger>
          <TabsTrigger value="all">
            All Users ({users.length})
          </TabsTrigger>
        </TabsList>

        {/* Pending Users */}
        <TabsContent value="pending">
          <Card className="bg-white/10 backdrop-blur-xl border-white/20">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Clock className="w-5 h-5 text-yellow-400" />
                Pending Registrations
              </CardTitle>
              <CardDescription className="text-gray-300">
                Approve or reject new user registrations
              </CardDescription>
            </CardHeader>
            <CardContent>
              {pendingUsers.length === 0 ? (
                <p className="text-center text-gray-400 py-8">No pending users</p>
              ) : (
                <div className="space-y-3">
                  {pendingUsers.map((user) => (
                    <div key={user.id} className="bg-white/5 rounded-lg p-4 border border-white/10">
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="text-white font-semibold">{user.name}</p>
                          <p className="text-gray-400 text-sm">{user.email}</p>
                          <p className="text-gray-500 text-xs mt-1">
                            Registered: {new Date(user.created_at).toLocaleString()}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            className="bg-green-600 hover:bg-green-700"
                            onClick={() => handleApproveUser(user.id)}
                            disabled={loading}
                          >
                            <UserCheck className="w-4 h-4 mr-1" /> Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-red-500/50 text-red-400 hover:bg-red-500/10"
                            onClick={() => handleRejectUser(user.id)}
                            disabled={loading}
                          >
                            <UserX className="w-4 h-4 mr-1" /> Reject
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Active Users */}
        <TabsContent value="active">
          <Card className="bg-white/10 backdrop-blur-xl border-white/20">
            <CardHeader>
              <CardTitle className="text-white">Active Users</CardTitle>
            </CardHeader>
            <CardContent>
              {activeUsers.length === 0 ? (
                <p className="text-center text-gray-400 py-8">No active users</p>
              ) : (
                <UserTable users={activeUsers} onSuspend={handleSuspendUser} onDelete={handleDeleteUser} onViewActivity={fetchUserActivity} setSelectedUser={setSelectedUser} />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Suspended Users */}
        <TabsContent value="suspended">
          <Card className="bg-white/10 backdrop-blur-xl border-white/20">
            <CardHeader>
              <CardTitle className="text-white">Suspended Users</CardTitle>
            </CardHeader>
            <CardContent>
              {suspendedUsers.length === 0 ? (
                <p className="text-center text-gray-400 py-8">No suspended users</p>
              ) : (
                <div className="space-y-3">
                  {suspendedUsers.map((user) => (
                    <div key={user.id} className="bg-white/5 rounded-lg p-4 border border-red-500/30">
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="text-white font-semibold">{user.name}</p>
                          <p className="text-gray-400 text-sm">{user.email}</p>
                          {getStatusBadge(user.status)}
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            className="bg-green-600 hover:bg-green-700"
                            onClick={() => handleActivateUser(user.id)}
                            disabled={loading}
                          >
                            <CheckCircle className="w-4 h-4 mr-1" /> Activate
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-red-500/50 text-red-400 hover:bg-red-500/10"
                            onClick={() => handleDeleteUser(user.id)}
                            disabled={loading}
                          >
                            <Trash2 className="w-4 h-4 mr-1" /> Delete
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* All Users */}
        <TabsContent value="all">
          <Card className="bg-white/10 backdrop-blur-xl border-white/20">
            <CardHeader>
              <CardTitle className="text-white">All Users</CardTitle>
            </CardHeader>
            <CardContent>
              <UserTable 
                users={users} 
                onSuspend={handleSuspendUser}
                onActivate={handleActivateUser}
                onDelete={handleDeleteUser}
                onViewActivity={fetchUserActivity}
                setSelectedUser={setSelectedUser}
                showAll={true}
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* User Activity Dialog */}
      {selectedUser && userActivity && (
        <Dialog open={!!selectedUser} onOpenChange={() => setSelectedUser(null)}>
          <DialogContent className="max-w-4xl bg-slate-900 border-white/20 max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-white">
                {userActivity.user.name}'s Activity
              </DialogTitle>
              <DialogDescription className="text-gray-400">
                {userActivity.user.email}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <Card className="bg-white/5">
                  <CardContent className="pt-4">
                    <p className="text-sm text-gray-400">EAs Generated</p>
                    <p className="text-2xl font-bold text-purple-400">{userActivity.ea_count}</p>
                  </CardContent>
                </Card>
                <Card className="bg-white/5">
                  <CardContent className="pt-4">
                    <p className="text-sm text-gray-400">Licenses Issued</p>
                    <p className="text-2xl font-bold text-blue-400">{userActivity.license_count}</p>
                  </CardContent>
                </Card>
                <Card className="bg-white/5">
                  <CardContent className="pt-4">
                    <p className="text-sm text-gray-400">Member Since</p>
                    <p className="text-sm text-white">{new Date(userActivity.user.created_at).toLocaleDateString()}</p>
                  </CardContent>
                </Card>
              </div>

              {userActivity.eas.length > 0 && (
                <div>
                  <h3 className="text-white font-semibold mb-2">Generated EAs</h3>
                  <div className="space-y-2">
                    {userActivity.eas.map((ea) => (
                      <div key={ea.id} className="bg-white/5 rounded p-3">
                        <p className="text-white">{ea.name}</p>
                        <p className="text-gray-400 text-sm">{ea.type} - {new Date(ea.created_at).toLocaleDateString()}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

// User Table Component
const UserTable = ({ users, onSuspend, onActivate, onDelete, onViewActivity, setSelectedUser, showAll }) => {
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-white/10">
            <th className="text-left text-gray-300 p-3">Name</th>
            <th className="text-left text-gray-300 p-3">Email</th>
            <th className="text-left text-gray-300 p-3">Status</th>
            <th className="text-left text-gray-300 p-3">Joined</th>
            <th className="text-left text-gray-300 p-3">Last Login</th>
            <th className="text-left text-gray-300 p-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id} className="border-b border-white/5 hover:bg-white/5">
              <td className="p-3 text-white">{user.name}</td>
              <td className="p-3 text-gray-300">{user.email}</td>
              <td className="p-3">
                {user.status === "pending" && <span className="text-yellow-400">⏳ Pending</span>}
                {user.status === "active" && <span className="text-green-400">✓ Active</span>}
                {user.status === "suspended" && <span className="text-red-400">✕ Suspended</span>}
              </td>
              <td className="p-3 text-gray-400 text-sm">{new Date(user.created_at).toLocaleDateString()}</td>
              <td className="p-3 text-gray-400 text-sm">{user.last_login ? new Date(user.last_login).toLocaleDateString() : "Never"}</td>
              <td className="p-3">
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-white/20 text-white hover:bg-white/10"
                    onClick={() => {
                      setSelectedUser(user);
                      onViewActivity(user.id);
                    }}
                  >
                    <Activity className="w-3 h-3 mr-1" /> View
                  </Button>
                  {user.status === "active" && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-yellow-500/50 text-yellow-400 hover:bg-yellow-500/10"
                      onClick={() => onSuspend(user.id)}
                    >
                      <Ban className="w-3 h-3" />
                    </Button>
                  )}
                  {user.status === "suspended" && onActivate && (
                    <Button
                      size="sm"
                      className="bg-green-600 hover:bg-green-700"
                      onClick={() => onActivate(user.id)}
                    >
                      <CheckCircle className="w-3 h-3" />
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-red-500/50 text-red-400 hover:bg-red-500/10"
                    onClick={() => onDelete(user.id)}
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AdminPanel;
