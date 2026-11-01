/*
Copyright 2026 Équipe Faso Cikan

SPDX-License-Identifier: AGPL-3.0-only
*/

import React, { type JSX } from "react";

import { MatrixClientPeg } from "../MatrixClientPeg";
import defaultDispatcher from "../dispatcher/dispatcher";
import { Action } from "../dispatcher/actions";
import { UserTab } from "../components/views/dialogs/UserTab";
import { useUserDisplayName } from "./utilisateur";

function ouvrirParametres(onglet?: UserTab): void {
    defaultDispatcher.dispatch({ action: Action.ViewUserSettings, initialTabId: onglet });
}

function initiales(nom: string): string {
    const mots = nom.trim().split(/\s+/);
    return ((mots[0]?.[0] ?? "") + (mots[1]?.[0] ?? "")).toUpperCase() || "?";
}

/** Barre du haut : marque, recherche, raccourcis et carte de l'agent connecté. */
export function BarreSuperieure(): JSX.Element {
    const userId = MatrixClientPeg.get()?.getUserId() ?? "";
    const nom = useUserDisplayName(userId);
    const matricule = userId.replace(/^@/, "").split(":")[0].toUpperCase();

    return (
        <header className="faso_Barre">
            <div className="faso_Barre_marque">
                <img src="faso/embleme.svg" alt="" width="34" height="34" />
                <span>
                    Faso Cikan<span className="faso_Barre_point">.</span>
                </span>
            </div>

            <button
                type="button"
                className="faso_Barre_recherche"
                onClick={() => defaultDispatcher.fire(Action.OpenSpotlight)}
            >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8" />
                    <path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
                <span>Rechercher une conversation, un agent...</span>
            </button>

            <div className="faso_Barre_actions">
                <button
                    type="button"
                    className="faso_Barre_rond"
                    title="Paramètres"
                    aria-label="Paramètres"
                    onClick={() => ouvrirParametres()}
                >
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6" />
                        <circle cx="12" cy="12" r="3.5" stroke="currentColor" strokeWidth="1.6" />
                        <path
                            d="m5.6 5.6 3.9 3.9m5 5 3.9 3.9m0-12.8-3.9 3.9m-5 5-3.9 3.9"
                            stroke="currentColor"
                            strokeWidth="1.6"
                        />
                    </svg>
                </button>
                <button
                    type="button"
                    className="faso_Barre_rond"
                    title="Notifications"
                    aria-label="Notifications"
                    onClick={() => ouvrirParametres(UserTab.Notifications)}
                >
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path
                            d="M6 10a6 6 0 1 1 12 0c0 4 1.5 6 2 6.5H4c.5-.5 2-2.5 2-6.5Z"
                            stroke="currentColor"
                            strokeWidth="1.6"
                            strokeLinejoin="round"
                        />
                        <path d="M10 19.5a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.6" />
                    </svg>
                </button>

                <button
                    type="button"
                    className="faso_Barre_rond"
                    title="Se déconnecter"
                    aria-label="Se déconnecter"
                    onClick={() => defaultDispatcher.dispatch({ action: "logout" })}
                >
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                        <path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4" stroke="currentColor" strokeWidth="1.6" />
                        <path d="M10 8l-4 4 4 4M6 12h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                    </svg>
                </button>

                <button type="button" className="faso_Barre_agent" onClick={() => ouvrirParametres(UserTab.Account)}>
                    <span className="faso_Barre_avatar" aria-hidden="true">
                        {initiales(nom)}
                    </span>
                    <span className="faso_Barre_identite">
                        <strong>{nom}</strong>
                        <small>Matricule {matricule}</small>
                    </span>
                </button>
            </div>
        </header>
    );
}
