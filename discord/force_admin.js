// this script allows you to access some features usually gated behind certain permissions
// for example, this lets you view roles, the list of members who have the said roles, emotes and other stuffs

// ====================================================================
// outdated and doesnt seem to work even on vanilla discord
// ====================================================================
let _mods; webpackChunkdiscord_app.push([[Symbol()],{},r=>_mods=r.c]);
webpackChunkdiscord_app.pop();
let findByProps = (...props) => {
    for (let m of Object.values(_mods)) {
        try {
            if (!m.exports || m.exports === window) continue;
            if (props.every((x) => m.exports?.[x])) return m.exports;

        for (let ex in m.exports) {
                if (props.every((x) => m.exports?.[ex]?.[x])) return m.exports[ex];
            }
        } catch {}
    }
}

let permStore = findByProps("canBasicChannel");
["can", "canAccessGuildSettings", "canAccessMemberSafetyPage", "canBasicChannel", "canImpersonateRole", "canManageUser", "canWithPartialContext", "isRoleHigher"].forEach(a => permStore.__proto__[a] = () => true);

// ====================================================================
// works under vencord, no idea if it works on vanilla discord or not
// ====================================================================
["can", "canAccessGuildSettings", "canAccessMemberSafetyPage", "canBasicChannel", "canImpersonateRole", "canManageUser", "canWithPartialContext", "isRoleHigher"].forEach(a => PermissionStore.__proto__[a] = () => true);
