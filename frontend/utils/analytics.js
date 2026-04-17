// analytics.js
import ReactGA from "react-ga4";

const GA_TRACKING_ID = import.meta.env.VITE_GA_TRACKING_ID;
const GA_TEST_MODE = import.meta.env.VITE_GA_TEST_MODE === "true";

export const initGA = () => {
  if (!import.meta.env.PROD && !GA_TEST_MODE) return;
  if (!GA_TRACKING_ID) return;

  ReactGA.initialize(GA_TRACKING_ID, { testMode: GA_TEST_MODE });
};

export const logPageView = (path) => {
  if (!import.meta.env.PROD && !GA_TEST_MODE) return;
  if (!GA_TRACKING_ID) return;

  ReactGA.send({ hitType: "pageview", page: path });
};
