/*
Copyright 2026 Équipe Faso Cikan

SPDX-License-Identifier: AGPL-3.0-only
*/

/*
 * Classification des messages.
 *
 * Un message classifié porte l'étiquette "bf.faso.classification" :
 *   - dans son contenu chiffré, où elle est authentifiée et sert à l'affichage ;
 *   - en clair à côté du texte chiffré (patch du SDK), pour que le serveur
 *     puisse faire expirer le message sans jamais le lire.
 */

import { type IContent, type MatrixEvent } from "matrix-js-sdk/src/matrix";

export const CLE_ETIQUETTE = "bf.faso.classification";

export type Niveau = "normal" | "restreint" | "confidentiel";

export interface Etiquette {
    niveau: Exclude<Niveau, "normal">;
    /** Délai d'expiration en secondes, compté depuis l'horodatage du serveur. */
    duree?: number;
}

export const NIVEAUX: Record<Niveau, { libelle: string; court: string }> = {
    normal: { libelle: "Non classifié", court: "Normal" },
    restreint: { libelle: "Diffusion restreinte", court: "Restreint" },
    confidentiel: { libelle: "Confidentiel", court: "Confidentiel" },
};

export const DELAIS: { secondes: number; libelle: string }[] = [
    { secondes: 30, libelle: "30 secondes" },
    { secondes: 60, libelle: "1 minute" },
    { secondes: 300, libelle: "5 minutes" },
    { secondes: 3600, libelle: "1 heure" },
    { secondes: 86400, libelle: "24 heures" },
    { secondes: 604800, libelle: "7 jours" },
];

export const DELAI_CONFIDENTIEL_PAR_DEFAUT = 300;

/* ------------------------------------------------------------------------ */
/* Choix courant, par salon                                                   */
/* ------------------------------------------------------------------------ */

export interface Choix {
    niveau: Niveau;
    duree?: number;
}

const NORMAL: Choix = { niveau: "normal" };
const choixParSalon = new Map<string, Choix>();
const abonnes = new Set<() => void>();

export function choixDuSalon(roomId: string): Choix {
    return choixParSalon.get(roomId) ?? NORMAL;
}

export function definirChoix(roomId: string, choix: Choix): void {
    if (choix.niveau === "normal") {
        choixParSalon.delete(roomId);
    } else if (choix.niveau === "confidentiel" && !choix.duree) {
        choixParSalon.set(roomId, { niveau: "confidentiel", duree: DELAI_CONFIDENTIEL_PAR_DEFAUT });
    } else {
        choixParSalon.set(roomId, { ...choix });
    }
    abonnes.forEach((f) => f());
}

export function sAbonner(rappel: () => void): () => void {
    abonnes.add(rappel);
    return () => abonnes.delete(rappel);
}

/** Ajoute l'étiquette du salon au contenu d'un message sur le point de partir. */
export function appliquerClassification(roomId: string, contenu: IContent): void {
    const choix = choixDuSalon(roomId);
    if (choix.niveau === "normal") return;

    const etiquette: Etiquette = { niveau: choix.niveau };
    if (choix.duree) etiquette.duree = choix.duree;
    contenu[CLE_ETIQUETTE] = etiquette;
}

/* ------------------------------------------------------------------------ */
/* Lecture d'un message reçu                                                  */
/* ------------------------------------------------------------------------ */

export function etiquetteDe(ev: MatrixEvent): Etiquette | null {
    // Priorité au contenu déchiffré, seul garanti par l'expéditeur.
    const brut = ev.getContent()[CLE_ETIQUETTE] ?? ev.getWireContent()[CLE_ETIQUETTE];
    if (!brut || typeof brut !== "object") return null;
    if (brut.niveau !== "restreint" && brut.niveau !== "confidentiel") return null;

    const duree = Number.isInteger(brut.duree) && brut.duree > 0 ? brut.duree : undefined;
    return { niveau: brut.niveau, duree };
}

export function estClassifie(ev: MatrixEvent): boolean {
    return etiquetteDe(ev) !== null;
}

export function echeanceDe(ev: MatrixEvent): number | null {
    const etiquette = etiquetteDe(ev);
    return etiquette?.duree ? ev.getTs() + etiquette.duree * 1000 : null;
}

export function formaterReste(ms: number): string {
    const s = Math.max(0, Math.ceil(ms / 1000));
    if (s < 60) return `${s} s`;
    if (s < 3600) {
        const m = Math.floor(s / 60);
        const r = s % 60;
        return r ? `${m} min ${String(r).padStart(2, "0")} s` : `${m} min`;
    }
    if (s < 86400) {
        const h = Math.floor(s / 3600);
        const m = Math.floor((s % 3600) / 60);
        return m ? `${h} h ${String(m).padStart(2, "0")}` : `${h} h`;
    }
    const j = Math.floor(s / 86400);
    const h = Math.floor((s % 86400) / 3600);
    return h ? `${j} j ${h} h` : `${j} j`;
}
