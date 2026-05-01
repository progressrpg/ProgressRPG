import { useEffect } from 'react';
import { useAuth } from '../../context/useAuth';
import { useNavigate } from 'react-router-dom';
import { useWebSocket } from '../../context/WebSocketContext';

export default function LogoutPage() {
  //console.log('[LogoutPage] mounted');
  const { logout } = useAuth();
  const { disconnect } = useWebSocket();
  const navigate = useNavigate();

  useEffect(() => {
    //console.log('[LogoutPage] Triggering logout...');
    disconnect?.(1000, 'logout');

    logout();

    const timer = setTimeout(() => {
      //console.log('[LogoutPage] Navigating to /');
      navigate('/');
    }, 800); // Slight delay for smoother UX

    return () => clearTimeout(timer); // Cleanup in case unmounted early
  }, [disconnect, logout, navigate]);

  return (
    <div>
      <h2>👋 Logging you out...</h2>
      <p>Please wait a moment.</p>
    </div>
  );
}
