import React, { lazy } from "react";
import { Navigate } from "react-router";
import FeatureToggle from "../components/FeatureToggle";

// Lazy load pages
const Home = lazy(() => import("../pages/Home/Home"));
const LoginPage = lazy(() => import("../pages/LoginPage/LoginPage"));
const LogoutPage = lazy(() => import("../pages/LogoutPage/LogoutPage"));
const RegisterPage = lazy(() => import("../pages/RegisterPage/RegisterPage"));
const PasswordResetConfirmPage = lazy(() =>
  import("../pages/PasswordResetConfirmPage/PasswordResetConfirmPage")
);
const PasswordResetRequestPage = lazy(() => import("../pages/PasswordResetRequestPage/PasswordResetRequestPage"));
const PrivacyPolicyPage = lazy(() => import("../pages/PrivacyPolicyPage/PrivacyPolicyPage"));
const TermsOfServicePage = lazy(() => import("../pages/TermsOfServicePage/TermsOfServicePage"));
const SupportPage = lazy(() => import("../pages/SupportPage/SupportPage"));
const ConfirmationPage = lazy(() => import("../pages/ConfirmationPage"));
const AccountPage = lazy(() => import("../pages/Account/Account"));
const EditAccount = lazy(() => import("../pages/EditAccount/EditAccount"));
const MapPage = lazy(() => import("../pages/MapPage/MapPage"));
const MaintenancePage = lazy(() => import("../pages/MaintenancePage/MaintenancePage"));
const UnavailablePage = lazy(() => import("../pages/UnavailablePage"));
const NotFoundPage = lazy(() => import("../pages/NotFoundPage/NotFoundPage"));
const LibraryPage = lazy(() => import("../pages/LibraryPage/LibraryPage"));
const ActivityTimelinePage = lazy(() => import("../pages/Game2/ActivityTimelinePage"))
const SuccessPage = lazy(() => import("../pages/SuccessPage"));
const CancelPage = lazy(() => import("../pages/CancelPage"));
const UpgradePage = lazy(() => import("../pages/Checkout/UpgradePage"));

import PrivateRoute from "../components/PrivateRoute";

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
    path: "/waitlist/redeem/:token",
    element: <RegisterPage />,
  },
  {
    path: "/reset-password/:key",
    element: <PasswordResetConfirmPage />,
  },
  {
    path: "/forgot-password",
    element: <PasswordResetRequestPage />,
  },
  {
    path: "/privacy-policy",
    element: <PrivacyPolicyPage />,
  },
  {
    path: "/terms-of-service",
    element: <TermsOfServicePage />,
  },
  {
    path: "/support",
    element: <SupportPage />,
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
    path: "/unavailable",
    element: <UnavailablePage />,
  },
  {
    path: "/timer",
    element: (
      <PrivateRoute>
        <ActivityTimelinePage />
      </PrivateRoute>
    ),
  },
  {
    path: "/map",
    element: (
      <PrivateRoute>
        <FeatureToggle flag="map">
          <MapPage />
        </FeatureToggle>
      </PrivateRoute>
    ),
  },
  {
    path: "/account",
    element: (
      <PrivateRoute>
        <AccountPage />
      </PrivateRoute>
    ),
  },
  {
    path: "/upgrade",
    element: (
      <PrivateRoute>
        <UpgradePage />
      </PrivateRoute>
    ),
  },
  {
    path: "/checkout",
    element: <Navigate to="/upgrade" replace />,
  },
  {
    path: "/payment-success",
    element: (
      <PrivateRoute>
        <SuccessPage />
      </PrivateRoute>
    ),
  },
  {
    path: "/payment-cancelled",
    element: (
      <PrivateRoute>
        <CancelPage />
      </PrivateRoute>
    ),
  },
  {
    path: "/edit-account",
    element: (
      <PrivateRoute>
        <EditAccount />
      </PrivateRoute>
    ),
  },
  {
    path: "/library",
    element: (
      <PrivateRoute>
        <LibraryPage />
      </PrivateRoute>
    ),
  },
  {
    path: "*",
    element: <NotFoundPage />,
  },
];
