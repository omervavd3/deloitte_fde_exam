import { useCallback, useEffect, useState } from "react";

import { api } from "../services/api";
import type { WeightProfile, WeightProfileInput } from "../types/profile";

export function useProfiles() {
  const [profiles, setProfiles] = useState<WeightProfile[]>([]);
  const [metrics, setMetrics] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [p, m] = await Promise.all([api.listProfiles(), api.listMetrics()]);
      setProfiles(p);
      setMetrics(m);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const save = useCallback(
    async (payload: WeightProfileInput, isNew: boolean) => {
      if (isNew) {
        await api.createProfile(payload);
      } else {
        const { name, ...rest } = payload;
        await api.updateProfile(name, rest);
      }
      await refresh();
    },
    [refresh],
  );

  const remove = useCallback(
    async (name: string) => {
      await api.deleteProfile(name);
      await refresh();
    },
    [refresh],
  );

  return { profiles, metrics, error, save, remove, refresh };
}
