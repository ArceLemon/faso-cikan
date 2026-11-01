/*
Copyright 2026 Équipe Faso Cikan

SPDX-License-Identifier: AGPL-3.0-only
*/

// Feuille de style de l'habillage Faso Cikan, servie avec la configuration
// (element/branding/faso.css) : on peut l'ajuster sans recompiler Element.
if (typeof document !== "undefined" && !document.getElementById("faso-habillage")) {
    const lien = document.createElement("link");
    lien.id = "faso-habillage";
    lien.rel = "stylesheet";
    lien.href = "faso/faso.css";
    document.head.appendChild(lien);
}

export {};
