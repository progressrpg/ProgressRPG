// PrivateRoute.tsx
import React from 'react';
import { Navigate } from 'react-router';
import { useAuth } from '../context/AuthContext';

interface PrivateRouteProps {
  children: React.ReactNode;
}

export default function PrivateRoute({ children }: PrivateRouteProps) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div role="status" aria-live="polite" aria-busy="true">
        <span className="sr-only">Loading...</span>
      </div>
    );
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}
