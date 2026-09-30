using FleetWise.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace FleetWise.Api.Controllers;

[ApiController]
[Route("api/dispatch")]
public class DispatchController : ControllerBase
{
    private readonly DispatcherService _dispatcher;
    private readonly IClock _clock;

    public DispatchController(DispatcherService dispatcher, IClock clock)
    {
        _dispatcher = dispatcher;
        _clock = clock;
    }

    public record DecisionRequest(int VehicleId, string ServiceType, int? TechnicianId);

    /// <summary>List vehicles whose scheduled service is overdue or due soon, for the calling tenant, with a suggested technician.</summary>
    [HttpGet(Name = "getDispatchLines")]
    public async Task<IActionResult> GetLines()
    {
        var (tenant, problem) = await ResolveAsync();
        if (problem is not null)
        {
            return problem;
        }

        var lines = await _dispatcher.GetLinesAsync(tenant!.TenantId);
        return Ok(new { generatedAt = _clock.UtcNow, count = lines.Count, lines });
    }

    /// <summary>Approve a dispatch line: creates a scheduled work order. FleetManager role only.</summary>
    [HttpPost("approve", Name = "approveDispatchLine")]
    public async Task<IActionResult> Approve(DecisionRequest request)
    {
        var (tenant, problem) = await ResolveAsync(requireManager: true);
        if (problem is not null)
        {
            return problem;
        }

        var (workOrder, error, status) = await _dispatcher.ApproveAsync(tenant!, request.VehicleId, request.ServiceType, request.TechnicianId);
        return status == 201 ? StatusCode(201, workOrder) : StatusCode(status, new { error });
    }

    /// <summary>Reject a dispatch line: records the decision, books nothing. FleetManager role only.</summary>
    [HttpPost("reject", Name = "rejectDispatchLine")]
    public async Task<IActionResult> Reject(DecisionRequest request)
    {
        var (tenant, problem) = await ResolveAsync(requireManager: true);
        if (problem is not null)
        {
            return problem;
        }

        var (error, status) = await _dispatcher.RejectAsync(tenant!, request.VehicleId, request.ServiceType);
        return status == 204 ? NoContent() : StatusCode(status, new { error });
    }

    private async Task<(TenantContext? Tenant, IActionResult? Problem)> ResolveAsync(bool requireManager = false)
    {
        if (!TenantContext.TryResolve(Request.Headers, out var tenant, out var error))
        {
            return (null, BadRequest(new { error }));
        }

        if (!await _dispatcher.TenantExistsAsync(tenant!.TenantId))
        {
            return (null, BadRequest(new { error = "Unknown tenant." })); // T026
        }

        if (requireManager && !tenant.IsFleetManager)
        {
            return (null, StatusCode(403, new { error = "Only FleetManager can approve or reject." }));
        }

        return (tenant, null);
    }
}
