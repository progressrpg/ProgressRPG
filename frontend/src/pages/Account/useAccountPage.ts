import { useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { useMutation } from "@tanstack/react-query";

import { useGame } from "../../hooks/useGame";
import { useAppConfig } from "../../hooks/useAppConfig";
import { deleteAccount, downloadUserData, updatePlayer } from "../../api/player";
import {
  getPlayerNameErrorMessage,
  getPlayerNameValidation,
} from "../../utils/playerNameValidation";
import { asArray } from "../../utils/arrayUtils";

function useAccountNameEditor({
  currentPlayerName,
  fetchPlayerAndCharacter,
}: {
  currentPlayerName: string;
  fetchPlayerAndCharacter: () => Promise<unknown>;
}) {
  const [isEditingName, setIsEditingName] = useState(false);
  const [draftName, setDraftName] = useState("");
  const [nameError, setNameError] = useState("");

  const nameValidation = useMemo(() => getPlayerNameValidation(draftName), [draftName]);

  const updateNameMutation = useMutation({
    mutationFn: updatePlayer,
    onSuccess: async () => {
      setNameError("");
      setIsEditingName(false);
      await fetchPlayerAndCharacter();
    },
    onError: (error) => {
      setNameError(getPlayerNameErrorMessage(error));
    },
  });

  const isSaveDisabled =
    updateNameMutation.isPending ||
    !nameValidation.isValid ||
    nameValidation.normalized === currentPlayerName;

  const handleStartEditingName = useCallback(() => {
    setDraftName(currentPlayerName);
    setNameError("");
    setIsEditingName(true);
  }, [currentPlayerName]);

  const handleCancelEditingName = useCallback(() => {
    setDraftName(currentPlayerName);
    setNameError("");
    setIsEditingName(false);
  }, [currentPlayerName]);

  const handleDraftNameChange = useCallback(
    (nextValue: string) => {
      setDraftName(nextValue);
      if (nameError) {
        setNameError("");
      }
    },
    [nameError]
  );

  const handleSaveName = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (isSaveDisabled) {
        return;
      }

      updateNameMutation.mutate({ name: nameValidation.normalized });
    },
    [isSaveDisabled, nameValidation.normalized, updateNameMutation]
  );

  return {
    isEditingName,
    draftName,
    nameError,
    nameValidation,
    updateNameMutation,
    isSaveDisabled,
    handleStartEditingName,
    handleCancelEditingName,
    handleDraftNameChange,
    handleSaveName,
  };
}

function useAccountDeletion() {
  const navigate = useNavigate();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");

  const deleteAccountMutation = useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => {
      localStorage.clear();
      sessionStorage.clear();
      navigate("/");
    },
  });

  const openDeleteConfirm = useCallback(() => {
    setShowDeleteConfirm(true);
  }, []);

  const closeDeleteConfirm = useCallback(() => {
    setShowDeleteConfirm(false);
    setDeleteConfirmText("");
  }, []);

  const handleDeleteConfirmTextChange = useCallback((nextText: string) => {
    setDeleteConfirmText(nextText);
  }, []);

  const handleDeleteAccount = useCallback(() => {
    if (deleteConfirmText === "DELETE") {
      deleteAccountMutation.mutate();
    }
  }, [deleteAccountMutation, deleteConfirmText]);

  return {
    showDeleteConfirm,
    deleteConfirmText,
    deleteAccountMutation,
    openDeleteConfirm,
    closeDeleteConfirm,
    handleDeleteConfirmTextChange,
    handleDeleteAccount,
  };
}

export function useAccountPage() {
  const { player, loading, fetchPlayerAndCharacter } = useGame();
  const { data: appConfig } = useAppConfig();

  const billingPortalUrl = appConfig?.stripe_billing_portal_url;

  const downloadUserDataMutation = useMutation({
    mutationFn: downloadUserData,
  });

  const currentPlayerName = player?.name?.trim() || "";

  const {
    isEditingName,
    draftName,
    nameError,
    nameValidation,
    updateNameMutation,
    isSaveDisabled,
    handleStartEditingName,
    handleCancelEditingName,
    handleDraftNameChange,
    handleSaveName,
  } = useAccountNameEditor({
    currentPlayerName,
    fetchPlayerAndCharacter,
  });

  const {
    showDeleteConfirm,
    deleteConfirmText,
    deleteAccountMutation,
    openDeleteConfirm,
    closeDeleteConfirm,
    handleDeleteConfirmTextChange,
    handleDeleteAccount,
  } = useAccountDeletion();

  const currentXp = player?.xp ?? 0;
  const nextLevelXp = player?.xp_next_level ?? 0;
  const totalTimeSeconds = player?.total_time ?? 0;
  const totalHours = Math.floor(totalTimeSeconds / 3600);
  const totalMinutes = Math.floor((totalTimeSeconds % 3600) / 60);
  const achievements = asArray(player?.achievements);
  const nameDisplay = loading ? "Loading..." : player?.name?.trim() || "Unnamed player";

  const isTrialing = player?.is_trialing ?? false;
  const [nowMs] = useState(() => Date.now());
  const trialDaysRemaining =
    isTrialing && player?.trial_end
      ? Math.max(
          0,
          Math.ceil(
            (new Date(player.trial_end).getTime() - nowMs) / (24 * 60 * 60 * 1000)
          )
        )
      : 0;

  const handleDownloadData = useCallback(() => {
    downloadUserDataMutation.mutate();
  }, [downloadUserDataMutation]);

  return {
    player,
    billingPortalUrl,
    currentXp,
    nextLevelXp,
    totalHours,
    totalMinutes,
    achievements,
    nameDisplay,
    isTrialing,
    trialDaysRemaining,
    isEditingName,
    draftName,
    nameError,
    nameValidation,
    updateNameMutation,
    isSaveDisabled,
    handleStartEditingName,
    handleCancelEditingName,
    handleDraftNameChange,
    handleSaveName,
    downloadUserDataMutation,
    handleDownloadData,
    showDeleteConfirm,
    deleteConfirmText,
    deleteAccountMutation,
    openDeleteConfirm,
    closeDeleteConfirm,
    handleDeleteConfirmTextChange,
    handleDeleteAccount,
  };
}
