using FleetWise.Api.Data;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace FleetWise.Api.Controllers;

// Legacy shortcut: this controller talks to the DbContext directly instead of going through a service.
[ApiController]
[Route("api/technicians")]
public class TechniciansController : ControllerBase
{
    private readonly FleetWiseDbContext _db;

    public TechniciansController(FleetWiseDbContext db)
    {
        _db = db;
    }

    [HttpGet]
    public async Task<IActionResult> GetAll([FromQuery] string? skill)
    {
        var technicians = await _db.Technicians.AsNoTracking().ToListAsync();
        if (!string.IsNullOrWhiteSpace(skill))
        {
            technicians = technicians
                .Where(t => t.Skills.Split(',', StringSplitOptions.TrimEntries).Contains(skill, StringComparer.OrdinalIgnoreCase))
                .ToList();
        }

        return Ok(technicians);
    }
}
