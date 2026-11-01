/*
Copyright 2026 Équipe Faso Cikan

SPDX-License-Identifier: AGPL-3.0-only
*/

import { useEffect, useState } from "react";

import { MatrixClientPeg } from "../MatrixClientPeg";

/** Nom affiché de l'agent, tel que fourni par l'annuaire (Keycloak via Synapse). */
export function useUserDisplayName(userId: string): string {
    const [nom, setNom] = useState(() => MatrixClientPeg.get()?.getUser(userId)?.displayName ?? "");

    useEffect(() => {
        let actif = true;
        MatrixClientPeg.get()
            ?.getProfileInfo(userId)
            .then((profil) => {
                if (actif && profil.displayname) setNom(profil.displayname);
            })
            .catch(() => undefined);
        return () => {
            actif = false;
        };
    }, [userId]);

    return nom || userId;
}
