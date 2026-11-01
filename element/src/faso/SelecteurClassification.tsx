/*
Copyright 2026 Équipe Faso Cikan

SPDX-License-Identifier: AGPL-3.0-only
*/

import React, { type JSX, useSyncExternalStore } from "react";

import { choixDuSalon, definirChoix, DELAIS, NIVEAUX, type Niveau, sAbonner } from "./classification";

const ORDRE: Niveau[] = ["normal", "restreint", "confidentiel"];

/** Bandeau placé au-dessus de la zone de saisie : niveau et délai d'effacement. */
export function SelecteurClassification({ roomId }: { roomId: string }): JSX.Element {
    const choix = useSyncExternalStore(sAbonner, () => choixDuSalon(roomId));
    const classifie = choix.niveau !== "normal";

    return (
        <div className={`faso_Selecteur faso_Selecteur--${choix.niveau}`}>
            <span className="faso_Selecteur_titre" id={`faso-niveau-${roomId}`}>
                Classification
            </span>

            <div className="faso_Selecteur_niveaux" role="radiogroup" aria-labelledby={`faso-niveau-${roomId}`}>
                {ORDRE.map((niveau) => (
                    <button
                        key={niveau}
                        type="button"
                        role="radio"
                        aria-checked={choix.niveau === niveau}
                        className={`faso_Selecteur_niveau faso_Selecteur_niveau--${niveau}`}
                        onClick={() => definirChoix(roomId, { niveau, duree: choix.duree })}
                    >
                        {NIVEAUX[niveau].court}
                    </button>
                ))}
            </div>

            {classifie && (
                <label className="faso_Selecteur_delai">
                    <span>Effacement</span>
                    <select
                        value={choix.duree ?? ""}
                        onChange={(e) =>
                            definirChoix(roomId, {
                                niveau: choix.niveau,
                                duree: e.target.value ? Number(e.target.value) : undefined,
                            })
                        }
                    >
                        {choix.niveau === "restreint" && <option value="">jamais</option>}
                        {DELAIS.map((d) => (
                            <option key={d.secondes} value={d.secondes}>
                                après {d.libelle}
                            </option>
                        ))}
                    </select>
                </label>
            )}

            {classifie && <span className="faso_Selecteur_regle">Transfert interdit</span>}
        </div>
    );
}
