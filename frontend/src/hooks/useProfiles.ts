import { useCallback, useEffect, useState } from "react";

import { api } from "../services/api";
import type {
  MetricCatalog,
  WeightProfile,
  WeightProfileInput,
} from "../types/profile";

const EMPTY_CATALOG: MetricCatalog = { metrics: [], redundant_pairs: [] };

export function useProfiles() {
  const [profiles, setProfiles] = useState<WeightProfile[]>([]);
  const [catalog, setCatalog] = useState<MetricCatalog>(EMPTY_CATALOG);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [p, c] = await Promise.all([api.listProfiles(), api.listMetrics()]);
      setProfiles(p);
      setCatalog(c);
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

  return { profiles, catalog, error, save, remove, refresh };
}
