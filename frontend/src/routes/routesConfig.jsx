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
const MaintenancePage = lazy(() => import("../pages/MaintenancePage/MaintenancePage"));
const SkillsPage = lazy(() => import("../pages/SkillsPage"));
const TasksPage = lazy(() => import("../pages/TasksPage"));
const ActivitiesPage = lazy(() => import("../pages/ActivitiesPage"));
const CategoriesPage = lazy(() => import("../pages/CategoriesPage"));

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
    path: "/profile",
    element: (
      <PrivateRoute>
        <ProfilePage />
      </PrivateRoute>
    ),
  },
  {
    path: "/skills",
    element: (
      <PrivateRoute>
        <SkillsPage />
      </PrivateRoute>
    ),
  },
  {
    path: "/tasks",
    element: (
      <PrivateRoute>
        <TasksPage />
      </PrivateRoute>
    ),
  },
  {
    path: "/activities",
    element: (
      <PrivateRoute>
        <ActivitiesPage />
      </PrivateRoute>
    ),
  },
  {
    path: "/categories",
    element: (
      <PrivateRoute>
        <CategoriesPage />
      </PrivateRoute>
    ),
  },
  {
    path: "*",
    element: <h2>404: Page Not Found</h2>,
  },
];
