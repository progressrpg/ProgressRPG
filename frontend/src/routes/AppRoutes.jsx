import React, { Suspense } from "react";
import { Routes, Route } from "react-router";
import { routes } from "./routesConfig";

function AppRoutes() {
  return (
    <Suspense fallback={<div>Loading page...</div>}>
      <Routes>
        {routes.map(({ path, element }, idx) => (
          <Route key={idx} path={path} element={element} />
        ))}
      </Routes>
    </Suspense>
  );
}

export default AppRoutes;
