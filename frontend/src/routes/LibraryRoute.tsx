import React from "react";
import ProgressiveUnlockGate from "../components/ProgressiveUnlockGate";
import LibraryPage from "../pages/LibraryPage/LibraryPage";

export default function LibraryRoute(): React.ReactElement {
  return (
    <ProgressiveUnlockGate
      unlock="library"
      title="Library locked"
      message="Complete 2 activities to unlock your Library."
    >
      <LibraryPage />
    </ProgressiveUnlockGate>
  );
}
