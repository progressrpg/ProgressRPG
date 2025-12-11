import React, { lazy } from "react";

// Lazy load pages
const Home = lazy(() => import("../pages/Home/Home"));
const LoginPage = lazy(() => import("../pages/LoginPage/LoginPage"));
const LogoutPage = lazy(() => import("../pages/LogoutPage/LogoutPage"));
const RegisterPage = lazy(() => import("../pages/RegisterPage/RegisterPage"));
const ConfirmationPage = lazy(() => import("../pages/ConfirmationPage"));
const OnboardingPage = lazy(() => import("../pages/OnboardingPage/OnboardingPage"));
const Game = lazy(() => import("../pages/Game/Game"));
const ProfilePage = lazy(() => import("../pages/Profile/Profile"));
const MapPage = lazy(() => import("../pages/MapPage/MapPage"));
const MaintenancePage = lazy(() => import("../pages/MaintenancePage/MaintenancePage"));

import PrivateRoute from "../components/PrivateRoute";
import RequireOnboardingComplete from "../components/RequireOnboardingComplete";

export const routes = [
  {
    path: "/",
    element: <Home />,
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/logout",
    element: <LogoutPage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },
  {
    path: "/confirm_email/:key",
    element: <ConfirmationPage />,
  },
  {
    path: "/maintenance",
    element: <MaintenancePage />,
  },
  {
    path: "/onboarding",
    element: (
      <PrivateRoute>
        <OnboardingPage />
      </PrivateRoute>
    ),
  },
  {
    path: "/game",
    element: (
      <PrivateRoute>
        <RequireOnboardingComplete>
          <Game />
        </RequireOnboardingComplete>
      </PrivateRoute>
    ),
  },
  {
    path: "/map",
    element: (
      <PrivateRoute>
        <RequireOnboardingComplete>
          <MapPage />
        </RequireOnboardingComplete>
      </PrivateRoute>
    ),
  },
  {
    path: "/profile",
    element: (
      <PrivateRoute>
        <ProfilePage />
      </PrivateRoute>
    ),
  },
  {
    path: "*",
    element: <h2>404: Page Not Found</h2>,
  },
];
