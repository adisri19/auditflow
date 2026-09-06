import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard';
import ReviewDashboard from './pages/ReviewDashboard';
import UploadPage from './pages/Upload';
import BatchList from './pages/BatchList';
import BatchDetail from './pages/BatchDetail';
import RecordDetail from './pages/RecordDetail';
import Login from './pages/Login';

// Create a React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Guarded Route component
const PrivateRoute = ({ children }) => {
  const token = localStorage.getItem('access_token');
  return token ? children : <Navigate to="/login" replace />;
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          {/* Public Login Route */}
          <Route path="/login" element={<Login />} />

          {/* Protected Main Routes */}
          <Route
            path="/"
            element={
              <PrivateRoute>
                <Layout>
                  <Dashboard />
                </Layout>
              </PrivateRoute>
            }
          />
          <Route
            path="/review"
            element={
              <PrivateRoute>
                <Layout>
                  <ReviewDashboard />
                </Layout>
              </PrivateRoute>
            }
          />
          <Route
            path="/upload"
            element={
              <PrivateRoute>
                <Layout>
                  <UploadPage />
                </Layout>
              </PrivateRoute>
            }
          />
          <Route
            path="/batches"
            element={
              <PrivateRoute>
                <Layout>
                  <BatchList />
                </Layout>
              </PrivateRoute>
            }
          />
          <Route
            path="/batches/:id"
            element={
              <PrivateRoute>
                <Layout>
                  <BatchDetail />
                </Layout>
              </PrivateRoute>
            }
          />
          <Route
            path="/records/:id"
            element={
              <PrivateRoute>
                <Layout>
                  <RecordDetail />
                </Layout>
              </PrivateRoute>
            }
          />

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
