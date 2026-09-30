using FleetWise.Api.Data;
using FleetWise.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace FleetWise.Api.Services;

/// <summary>
/// Overdue maintenance dispatcher (spec 001). Every method takes the tenant explicitly
/// and scopes every query by it (constitution Principle II).
/// </summary>
public class DispatcherService
{
    private readonly FleetWiseDbContext _db;
    private readonly IClock _clock;
    private readonly TechnicianMatcher _matcher;

    public DispatcherService(FleetWiseDbContext db, IClock clock)
    {
        _db = db;
        _clock = clock;
        _matcher = new TechnicianMatcher(db, clock);
    }

    public Task<bool> TenantExistsAsync(int tenantId) => _db.Tenants.AnyAsync(t => t.Id == tenantId);

    /// <summary>US1: vehicles of this tenant with a scheduled service overdue or due within 7 days.</summary>
    public async Task<List<DispatchLine>> GetLinesAsync(int tenantId)
    {
        var today = _clock.UtcNow.Date;
        var dueSoonDays = await _db.Tenants.Where(t => t.Id == tenantId).Select(t => t.DueSoonDays).FirstOrDefaultAsync();
        if (dueSoonDays <= 0)
        {
            dueSoonDays = 7;
        }

        var vehicles = await _db.Vehicles.AsNoTracking()
            .Where(v => v.TenantId == tenantId)
            .ToListAsync();
        var schedules = await _db.MaintenanceSchedules.AsNoTracking().ToListAsync();
        var records = await _db.MaintenanceRecords.AsNoTracking()
            .Where(r => r.TenantId == tenantId)
            .ToListAsync();
        var openWorkOrders = await _db.WorkOrders.AsNoTracking()
            .Where(w => w.TenantId == tenantId && (w.Status == WorkOrderStatus.Draft || w.Status == WorkOrderStatus.Scheduled))
            .Select(w => new { w.VehicleId, w.ServiceType })
            .ToListAsync();

        var lines = new List<DispatchLine>();
        foreach (var vehicle in vehicles)
        {
            foreach (var schedule in schedules.Where(s => s.VehicleClass == vehicle.VehicleClass))
            {
                var last = records
                    .Where(r => r.VehicleId == vehicle.Id && r.ServiceType == schedule.ServiceType)
                    .OrderByDescending(r => r.PerformedOn)
                    .FirstOrDefault();

                DispatchStatus status;
                DispatchTrigger trigger;
                int? kmOverdue = null;
                int daysUntilDue;

                if (last is null)
                {
                    status = DispatchStatus.Overdue;
                    trigger = DispatchTrigger.NoHistory;
                    daysUntilDue = 0;
                }
                else
                {
                    var kmSince = vehicle.OdometerKm - last.OdometerKm;
                    var daysSince = (int)(today - last.PerformedOn.Date).TotalDays;
                    daysUntilDue = schedule.IntervalDays - daysSince;

                    if (kmSince > schedule.IntervalKm)
                    {
                        status = DispatchStatus.Overdue;
                        trigger = DispatchTrigger.Distance;
                        kmOverdue = kmSince - schedule.IntervalKm;
                    }
                    else if (daysUntilDue < 0)
                    {
                        status = DispatchStatus.Overdue;
                        trigger = DispatchTrigger.Date;
                    }
                    else if (daysUntilDue <= dueSoonDays)
                    {
                        status = DispatchStatus.DueSoon;
                        trigger = DispatchTrigger.Date;
                    }
                    else
                    {
                        continue;
                    }
                }

                if (openWorkOrders.Any(w => w.VehicleId == vehicle.Id && w.ServiceType == schedule.ServiceType))
                {
                    status = DispatchStatus.AlreadyHandled;
                }

                TechnicianSuggestion? suggestion = null;
                if (status != DispatchStatus.AlreadyHandled)
                {
                    suggestion = await _matcher.SuggestAsync(tenantId, schedule.RequiredSkill);
                }

                lines.Add(new DispatchLine(vehicle.Id, vehicle.UnitNumber, schedule.ServiceType, status, trigger, kmOverdue, daysUntilDue, suggestion));
            }
        }

        return lines
            .OrderBy(l => l.Status)
            .ThenByDescending(l => l.KmOverdue ?? 0)
            .ThenBy(l => l.DaysUntilDue)
            .ToList();
    }

    /// <summary>US3: approve a dispatch line. Creates a scheduled work order for the next business day.</summary>
    public async Task<(WorkOrder? WorkOrder, string? Error, int Status)> ApproveAsync(TenantContext tenant, int vehicleId, string serviceType, int? technicianId)
    {
        var line = (await GetLinesAsync(tenant.TenantId)).FirstOrDefault(l => l.VehicleId == vehicleId && l.ServiceType == serviceType);
        if (line is null)
        {
            return (null, "No dispatch line for this vehicle and service in your tenant.", 404);
        }

        if (line.Status == DispatchStatus.AlreadyHandled)
        {
            return (null, "An open work order already exists for this vehicle and service.", 409);
        }

        var techId = technicianId ?? line.Suggestion?.TechnicianId;
        if (techId is not null && !await _db.Technicians.AnyAsync(t => t.Id == techId && t.TenantId == tenant.TenantId))
        {
            return (null, "Technician not found in your tenant.", 404);
        }

        var workOrder = new WorkOrder
        {
            TenantId = tenant.TenantId,
            VehicleId = vehicleId,
            ServiceType = serviceType,
            TechnicianId = techId,
            Status = WorkOrderStatus.Scheduled,
            CreatedOn = _clock.UtcNow,
            ScheduledFor = NextBusinessDay(_clock.UtcNow.Date),
            Notes = $"Approved by {tenant.UserName} via dispatcher"
        };
        _db.WorkOrders.Add(workOrder);
        await _db.SaveChangesAsync();

        _db.DispatchDecisions.Add(new DispatchDecision
        {
            TenantId = tenant.TenantId,
            VehicleId = vehicleId,
            ServiceType = serviceType,
            Outcome = DispatchOutcome.Approved,
            TechnicianId = techId,
            WorkOrderId = workOrder.Id,
            DecidedBy = tenant.UserName ?? "unknown",
            DecidedOn = _clock.UtcNow
        });
        await _db.SaveChangesAsync();
        return (workOrder, null, 201);
    }

    /// <summary>US3: reject a dispatch line. Records the decision; the vehicle stays on the list.</summary>
    public async Task<(string? Error, int Status)> RejectAsync(TenantContext tenant, int vehicleId, string serviceType)
    {
        var exists = (await GetLinesAsync(tenant.TenantId)).Any(l => l.VehicleId == vehicleId && l.ServiceType == serviceType);
        if (!exists)
        {
            return ("No dispatch line for this vehicle and service in your tenant.", 404);
        }

        _db.DispatchDecisions.Add(new DispatchDecision
        {
            TenantId = tenant.TenantId,
            VehicleId = vehicleId,
            ServiceType = serviceType,
            Outcome = DispatchOutcome.Rejected,
            DecidedBy = tenant.UserName ?? "unknown",
            DecidedOn = _clock.UtcNow
        });
        await _db.SaveChangesAsync();
        return (null, 204);
    }

    private static DateTime NextBusinessDay(DateTime date)
    {
        var next = date.AddDays(1);
        while (next.DayOfWeek is DayOfWeek.Saturday or DayOfWeek.Sunday)
        {
            next = next.AddDays(1);
        }

        return next;
    }
}
