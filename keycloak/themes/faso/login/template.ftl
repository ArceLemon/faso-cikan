<#import "field.ftl" as field>
<#import "footer.ftl" as loginFooter>
<#macro username>
  <@field.group name="username" label=msg("username")>
    <div class="${properties.kcInputGroup}">
      <div class="${properties.kcInputGroupItemClass} ${properties.kcFill}">
        <span class="${properties.kcInputClass} ${properties.kcFormReadOnlyClass}">
          <input id="kc-attempted-username" value="${auth.attemptedUsername?upper_case}" readonly>
        </span>
      </div>
      <div class="${properties.kcInputGroupItemClass}">
        <button id="reset-login" class="${properties.kcFormPasswordVisibilityButtonClass}" type="button"
              aria-label="${msg('restartLoginTooltip')}" title="${msg('restartLoginTooltip')}"
              onclick="location.href='${url.loginRestartFlowUrl}'">
            <i class="fa-sync-alt fas" aria-hidden="true"></i>
        </button>
      </div>
    </div>
  </@field.group>
</#macro>

<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<!DOCTYPE html>
<html class="${properties.kcHtmlClass!} faso" lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light">
    <meta name="robots" content="noindex, nofollow">
    <title>${msg("fasoTitre")}</title>
    <link rel="icon" href="${url.resourcesPath}/img/embleme.svg" type="image/svg+xml">
    <#if properties.stylesCommon?has_content>
        <#list properties.stylesCommon?split(' ') as style>
            <link href="${url.resourcesCommonPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>
    <#if properties.styles?has_content>
        <#list properties.styles?split(' ') as style>
            <link href="${url.resourcesPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>
    <script type="module" src="${url.resourcesPath}/js/passwordVisibility.js"></script>
    <script type="module">
        <#outputformat "JavaScript">
        import { startSessionPolling } from ${(url.resourcesPath + "/js/authChecker.js")?c};
        startSessionPolling(${url.ssoLoginInOtherTabsUrl?c});
        </#outputformat>
    </script>
    <#if authenticationSession??>
        <script type="module">
            <#outputformat "JavaScript">
            import { checkAuthSession } from ${(url.resourcesPath + "/js/authChecker.js")?c};
            checkAuthSession(${authenticationSession.authSessionIdHash?c});
            </#outputformat>
        </script>
    </#if>
</head>

<body class="faso-page" data-page-id="login-${pageId}">
<div class="faso-cadre">

  <main class="faso-formulaire">
    <div class="faso-marque">
      <img src="${url.resourcesPath}/img/embleme.svg" alt="" width="34" height="34">
      <span>Faso Cikan<span class="faso-point">.</span></span>
    </div>

    <div class="faso-formulaire__contenu">
      <h1 id="kc-page-title"><#nested "header"></h1>
      <p class="faso-sous-titre">${msg("fasoSousTitre")}</p>

      <#if auth?has_content && auth.showUsername() && !auth.showResetCredentials()>
        <div class="${properties.kcFormClass!}">
          <#nested "show-username">
          <@username />
        </div>
      </#if>

      <#if displayMessage && message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
        <div class="faso-alerte faso-alerte--${message.type}" role="alert">
          ${kcSanitize(message.summary)?no_esc}
        </div>
      </#if>

      <#nested "form">

      <#if auth?has_content && auth.showTryAnotherWayLink()>
        <form id="kc-select-try-another-way-form" action="${url.loginAction}" method="post" novalidate="novalidate">
          <input type="hidden" name="tryAnotherWay" value="on"/>
          <button type="submit" class="faso-lien">${msg("doTryAnotherWay")}</button>
        </form>
      </#if>

      <#if displayInfo>
        <div id="kc-info" class="faso-info"><#nested "info"></div>
      </#if>
    </div>

    <p class="faso-pied">${msg("fasoPied")}</p>
  </main>

  <aside class="faso-vitrine" aria-hidden="true">
    <div class="faso-vitrine__texte">
      <h2>${msg("fasoVitrineTitre")}</h2>
      <ul>
        <li><span class="faso-coche"></span>${msg("fasoGarantie1")}</li>
        <li><span class="faso-coche"></span>${msg("fasoGarantie2")}</li>
        <li><span class="faso-coche"></span>${msg("fasoGarantie3")}</li>
      </ul>
    </div>
    <div class="faso-vitrine__ecran">
      <img src="${url.resourcesPath}/img/apercu.png" alt="" width="1440" height="900">
    </div>
  </aside>

</div>
</body>
</html>
</#macro>
