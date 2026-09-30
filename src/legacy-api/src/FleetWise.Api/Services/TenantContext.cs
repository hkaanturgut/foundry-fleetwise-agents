using Microsoft.AspNetCore.Http;

namespace FleetWise.Api.Services;

/// <summary>
/// Who is calling and for which tenant, resolved once per request from headers
/// (a stand-in for real authentication claims). Passed explicitly to services.
/// </summary>
public sealed record TenantContext(int TenantId, string? Role, string? UserName)
{
    public const string TenantHeader = "X-Tenant-Id";
    public const string RoleHeader = "X-User-Role";
    public const string UserHeader = "X-User-Name";
    public const string FleetManagerRole = "FleetManager";

    public bool IsFleetManager => string.Equals(Role, FleetManagerRole, StringComparison.Ordinal);

    public static bool TryResolve(IHeaderDictionary headers, out TenantContext? context, out string error)
    {
        context = null;
        if (!headers.TryGetValue(TenantHeader, out var raw) || string.IsNullOrWhiteSpace(raw))
        {
            error = $"Missing {TenantHeader} header.";
            return false;
        }

        if (!int.TryParse(raw.ToString(), out var tenantId) || tenantId <= 0)
        {
            error = $"{TenantHeader} must be a positive integer.";
            return false;
        }

        headers.TryGetValue(RoleHeader, out var role);
        headers.TryGetValue(UserHeader, out var user);
        context = new TenantContext(tenantId, role.ToString(), user.ToString());
        error = string.Empty;
        return true;
    }
}
