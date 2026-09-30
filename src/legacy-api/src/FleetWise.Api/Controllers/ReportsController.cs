using FleetWise.Api.Data;
using FleetWise.Api.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace FleetWise.Api.Controllers;

// Legacy shortcut: business logic and data access live in the controller.
[ApiController]
[Route("api/reports")]
public class ReportsController : ControllerBase
{
    private readonly FleetWiseDbContext _db;
    private readonly IClock _clock;

    public ReportsController(FleetWiseDbContext db, IClock clock)
    {
        _db = db;
        _clock = clock;
    }

    /// <summary>
    /// "Overdue" report used by the ops team since 2019.
    /// Hard-coded rule: a vehicle is overdue if it has driven more than 10,000 km since its most
    /// recent service of ANY type. It ignores MaintenanceSchedules and the date intervals entirely.
    /// </summary>
    [HttpGet("overdue")]
    public async Task<IActionResult> Overdue()
    {
        var vehicles = await _db.Vehicles.Include(v => v.MaintenanceRecords).AsNoTracking().ToListAsync();

        var overdue = vehicles
            .Select(v => new
            {
                v.Id,
                v.TenantId,
                v.UnitNumber,
                LastServiceKm = v.MaintenanceRecords.Count == 0 ? 0 : v.MaintenanceRecords.Max(r => r.OdometerKm),
                v.OdometerKm
            })
            .Where(v => v.OdometerKm - v.LastServiceKm > 10000)
            .Select(v => new { v.Id, v.TenantId, v.UnitNumber, KmSinceLastService = v.OdometerKm - v.LastServiceKm })
            .OrderByDescending(v => v.KmSinceLastService)
            .ToList();

        return Ok(new { generatedAt = _clock.UtcNow, count = overdue.Count, vehicles = overdue });
    }
}
