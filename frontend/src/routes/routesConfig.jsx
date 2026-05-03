import React, { lazy } from "react";
import { Navigate } from "react-router-dom";
import FeatureToggle from "../components/FeatureToggle";

// Lazy load pages
const Home = lazy(() => import("../pages/Home/Home"));
const LoginPage = lazy(() => import("../pages/LoginPage/LoginPage"));
const LogoutPage = lazy(() => import("../pages/LogoutPage/LogoutPage"));
const RegisterPage = lazy(() => import("../pages/RegisterPage/RegisterPage"));
const PasswordResetConfirmPage = lazy(() =>
  import("../pages/PasswordResetConfirmPage/PasswordResetConfirmPage")
);
const ForgotPasswordPage = lazy(() => import("../pages/ForgotPasswordPage/ForgotPasswordPage"));
const PrivacyPolicyPage = lazy(() => import("../pages/PrivacyPolicyPage/PrivacyPolicyPage"));
const TermsOfServicePage = lazy(() => import("../pages/TermsOfServicePage/TermsOfServicePage"));
const SupportPage = lazy(() => import("../pages/SupportPage/SupportPage"));
const ConfirmationPage = lazy(() => import("../pages/ConfirmationPage"));
const OnboardingPage = lazy(() => import("../pages/OnboardingPage/OnboardingPage"));
const AccountPage = lazy(() => import("../pages/Account/Account"));
const EditAccount = lazy(() => import("../pages/EditAccount/EditAccount"));
//const VillagePage = lazy(() => import("../pages/VillagePage/VillagePage"));
const MaintenancePage = lazy(() => import("../pages/MaintenancePage/MaintenancePage"));
const NotFoundPage = lazy(() => import("../pages/NotFoundPage/NotFoundPage"));
// const SkillsPage = lazy(() => import("../pages/SkillsPage/SkillsPage"));
const TasksPage = lazy(() => import("../pages/TasksPage/TasksPage"));
const ProjectsPage = lazy(() => import("../pages/ProjectsPage/ProjectsPage"));
const ActivitiesPage = lazy(() => import("../pages/ActivitiesPage"));
// const CategoriesPage = lazy(() => import("../pages/CategoriesPage/CategoriesPage"));
const ActivityTimelinePage = lazy(() => import("../pages/Game2/ActivityTimelinePage"))
const SuccessPage = lazy(() => import("../pages/SuccessPage"));
const CancelPage = lazy(() => import("../pages/CancelPage"));
const UpgradePage = lazy(() => import("../pages/Checkout/UpgradePage"));

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
    path: "/reset-password/:key",
    element: <PasswordResetConfirmPage />,
  },
  {
    path: "/forgot-password",
    element: <ForgotPasswordPage />,
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
    path: "/onboarding",
    element: (
      <PrivateRoute>
        <OnboardingPage />
      </PrivateRoute>
    ),
  },
  {
    path: "/timer",
    element: (
      <PrivateRoute>
        <RequireOnboardingComplete>
          <ActivityTimelinePage />
        </RequireOnboardingComplete>
      </PrivateRoute>
    ),
  },
  /* {
    path: "/village",
    element: (
      <PrivateRoute>
        <RequireOnboardingComplete>
          <VillagePage />
        </RequireOnboardingComplete>
      </PrivateRoute>
    ),
  }, */
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
    path: "/upgrade",
    element: (
      <PrivateRoute>
        <RequireOnboardingComplete>
          <UpgradePage />
        </RequireOnboardingComplete>
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
        <RequireOnboardingComplete>
          <SuccessPage />
        </RequireOnboardingComplete>
      </PrivateRoute>
    ),
  },
  {
    path: "/payment-cancelled",
    element: (
      <PrivateRoute>
        <RequireOnboardingComplete>
          <CancelPage />
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
  // {
  //   path: "/skills",
  //   element: (
  //     <PrivateRoute>
  //       <RequireOnboardingComplete>
  //         <SkillsPage />
  //       </RequireOnboardingComplete>
  //     </PrivateRoute>
  //   ),
  // },
  {
    path: "/tasks",
    element: (
      <PrivateRoute>
        <RequireOnboardingComplete>
          <FeatureToggle
            flag="tasksPage"
          >
            <TasksPage />
          </FeatureToggle>
        </RequireOnboardingComplete>
      </PrivateRoute>
    ),
  },
  {
    path: "/projects",
    element: (
      <PrivateRoute>
        <RequireOnboardingComplete>
          <FeatureToggle flag="projectsPage">
            <ProjectsPage />
          </FeatureToggle>
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
  // {
  //   path: "/categories",
  //   element: (
  //     <PrivateRoute>
  //       <RequireOnboardingComplete>
  //         <CategoriesPage />
  //       </RequireOnboardingComplete>
  //     </PrivateRoute>
  //   ),
  // },
  // Premium-only route pattern:
  // {
  //   path: "/premium-example",
  //   element: (
  //     <PrivateRoute>
  //       <RequireOnboardingComplete>
  //         <RequirePremium>
  //           <SomePremiumPage />
  //         </RequirePremium>
  //       </RequireOnboardingComplete>
  //     </PrivateRoute>
  //   ),
  // },
  {
    path: "*",
    element: <NotFoundPage />,
  },
];
