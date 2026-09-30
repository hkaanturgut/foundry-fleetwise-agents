using FleetWise.Api.Data;
using FleetWise.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace FleetWise.Api.Services;

/// <summary>US2: suggests a qualified technician from the requesting tenant only (FR-004, FR-010, FR-011).</summary>
public class TechnicianMatcher
{
    private readonly FleetWiseDbContext _db;
    private readonly IClock _clock;

    public TechnicianMatcher(FleetWiseDbContext db, IClock clock)
    {
        _db = db;
        _clock = clock;
    }

    public async Task<TechnicianSuggestion> SuggestAsync(int tenantId, string requiredSkill)
    {
        var technicians = (await _db.Technicians.AsNoTracking().Where(t => t.TenantId == tenantId).ToListAsync())
            .Where(t => t.Skills.Split(',', StringSplitOptions.TrimEntries).Contains(requiredSkill, StringComparer.OrdinalIgnoreCase))
            .ToList();

        if (technicians.Count == 0)
        {
            return new TechnicianSuggestion(null, null, NoQualifiedTechnician: true);
        }

        var windowEnd = _clock.UtcNow.AddDays(7);
        var load = await _db.WorkOrders.AsNoTracking()
            .Where(w => w.TenantId == tenantId && w.Status == WorkOrderStatus.Scheduled && w.TechnicianId != null && w.ScheduledFor <= windowEnd)
            .GroupBy(w => w.TechnicianId!.Value)
            .Select(g => new { TechnicianId = g.Key, Count = g.Count() })
            .ToDictionaryAsync(x => x.TechnicianId, x => x.Count);

        var pick = technicians
            .OrderBy(t => load.GetValueOrDefault(t.Id))
            .ThenBy(t => t.Name, StringComparer.Ordinal)
            .First();

        return new TechnicianSuggestion(pick.Id, pick.Name, NoQualifiedTechnician: false);
    }
}
