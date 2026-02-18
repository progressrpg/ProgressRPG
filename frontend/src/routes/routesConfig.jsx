import React, { lazy } from "react";

// Lazy load pages
const Home = lazy(() => import("../pages/Home/Home"));
const LoginPage = lazy(() => import("../pages/LoginPage/LoginPage"));
const LogoutPage = lazy(() => import("../pages/LogoutPage/LogoutPage"));
const RegisterPage = lazy(() => import("../pages/RegisterPage/RegisterPage"));
const ConfirmationPage = lazy(() => import("../pages/ConfirmationPage"));
const OnboardingPage = lazy(() => import("../pages/OnboardingPage/OnboardingPage"));
const AccountPage = lazy(() => import("../pages/Account/Account"));
const EditAccount = lazy(() => import("../pages/EditAccount/EditAccount"));
const MaintenancePage = lazy(() => import("../pages/MaintenancePage/MaintenancePage"));
const SkillsPage = lazy(() => import("../pages/SkillsPage"));
const TasksPage = lazy(() => import("../pages/TasksPage"));
const ActivitiesPage = lazy(() => import("../pages/ActivitiesPage"));
const CategoriesPage = lazy(() => import("../pages/CategoriesPage"));
const ActivityTimelinePage = lazy(() => import("../pages/Game2/ActivityTimelinePage"))

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
          <ActivityTimelinePage />
        </RequireOnboardingComplete>
      </PrivateRoute>
    ),
  },
  {
    path: "/account",
    element: (
      <PrivateRoute>
          <RequireOnboardingComplete>
          <AccountPage />
        </RequireOnboardingComplete>
      </PrivateRoute>
    ),
  },
  {
    path: "/edit-account",
    element: (
      <PrivateRoute>
        <RequireOnboardingComplete>
          <EditAccount />
        </RequireOnboardingComplete>
      </PrivateRoute>
    ),
  },
  {
    path: "/skills",
    element: (
      <PrivateRoute>
        <RequireOnboardingComplete>
          <SkillsPage />
        </RequireOnboardingComplete>
      </PrivateRoute>
    ),
  },
  {
    path: "/tasks",
    element: (
      <PrivateRoute>
        <RequireOnboardingComplete>
          <TasksPage />
        </RequireOnboardingComplete>
      </PrivateRoute>
    ),
  },
  {
    path: "/activities",
    element: (
      <PrivateRoute>
        <RequireOnboardingComplete>
          <ActivitiesPage />
        </RequireOnboardingComplete>
      </PrivateRoute>
    ),
  },
  {
    path: "/categories",
    element: (
      <PrivateRoute>
        <RequireOnboardingComplete>
          <CategoriesPage />
        </RequireOnboardingComplete>
      </PrivateRoute>
    ),
  },
  {
    path: "*",
    element: <h2>404: Page Not Found</h2>,
  },
];
