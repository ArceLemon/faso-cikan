/*
Copyright 2026 Équipe Faso Cikan

SPDX-License-Identifier: AGPL-3.0-only
*/

import React, { type JSX, type ReactNode, useEffect, useState } from "react";
import { type MatrixEvent } from "matrix-js-sdk/src/matrix";

import { echeanceDe, etiquetteDe, formaterReste, NIVEAUX } from "./classification";

/**
 * Entoure le corps d'un message classifié : bandeau de niveau, compte à rebours,
 * puis masquage du contenu à l'échéance. Le serveur rédacte le message au même
 * moment ; ce masquage couvre l'intervalle avant la synchronisation.
 */
export function CadreClassification({ mxEvent, children }: { mxEvent: MatrixEvent; children: ReactNode }): JSX.Element {
    const etiquette = etiquetteDe(mxEvent);
    const echeance = echeanceDe(mxEvent);
    const [maintenant, setMaintenant] = useState(() => Date.now());

    useEffect(() => {
        if (echeance === null || Date.now() >= echeance) return;
        const minuterie = window.setInterval(() => setMaintenant(Date.now()), 1000);
        return () => window.clearInterval(minuterie);
    }, [echeance]);

    if (!etiquette) return <>{children}</>;

    const expire = echeance !== null && maintenant >= echeance;
    let regle = "Ne pas transférer";
    if (expire) regle = "Expiré";
    else if (echeance !== null) regle = `S'efface dans ${formaterReste(echeance - maintenant)}`;

    return (
        <div className={`faso_Cadre faso_Cadre--${etiquette.niveau}${expire ? " faso_Cadre--expire" : ""}`}>
            <div className="faso_Cadre_bandeau">
                <span className="faso_Cadre_niveau">{NIVEAUX[etiquette.niveau].libelle}</span>
                <span className="faso_Cadre_regle" aria-live="off">
                    {regle}
                </span>
            </div>
            {expire ? (
                <p className="faso_Cadre_expire">Ce message a expiré. Son contenu a été effacé.</p>
            ) : (
                <div className="faso_Cadre_corps">{children}</div>
            )}
        </div>
    );
}
