using FleetWise.Api.Data;
using FleetWise.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace FleetWise.Api.Services;

public interface IClock
{
    DateTime UtcNow { get; }
}

public class SystemClock : IClock
{
    public DateTime UtcNow => DateTime.UtcNow;
}

public interface IVehicleService
{
    Task<List<Vehicle>> GetAllAsync();
    Task<Vehicle?> GetByIdAsync(int id);
    Task<Vehicle?> UpdateOdometerAsync(int id, int odometerKm);
}

public class VehicleService : IVehicleService
{
    private readonly FleetWiseDbContext _db;

    public VehicleService(FleetWiseDbContext db)
    {
        _db = db;
    }

    // Legacy: returns vehicles for ALL tenants.
    public Task<List<Vehicle>> GetAllAsync() =>
        _db.Vehicles.AsNoTracking().OrderBy(v => v.Id).ToListAsync();

    public Task<Vehicle?> GetByIdAsync(int id) =>
        _db.Vehicles.Include(v => v.MaintenanceRecords).AsNoTracking().FirstOrDefaultAsync(v => v.Id == id);

    public async Task<Vehicle?> UpdateOdometerAsync(int id, int odometerKm)
    {
        var vehicle = await _db.Vehicles.FindAsync(id);
        if (vehicle is null)
        {
            return null;
        }

        if (odometerKm < vehicle.OdometerKm)
        {
            throw new ArgumentException("Odometer cannot go backwards.");
        }

        vehicle.OdometerKm = odometerKm;
        await _db.SaveChangesAsync();
        return vehicle;
    }
}

public record CreateWorkOrderRequest(int TenantId, int VehicleId, string ServiceType, string? Notes);

public interface IWorkOrderService
{
    Task<List<WorkOrder>> GetAllAsync();
    Task<WorkOrder?> GetByIdAsync(int id);
    Task<WorkOrder> CreateAsync(CreateWorkOrderRequest request);
    Task<WorkOrder?> ScheduleAsync(int id, DateTime scheduledFor, int technicianId);
    Task<WorkOrder?> CompleteAsync(int id, string technicianNotes);
}

public class WorkOrderService : IWorkOrderService
{
    private readonly FleetWiseDbContext _db;
    private readonly IClock _clock;

    public WorkOrderService(FleetWiseDbContext db, IClock clock)
    {
        _db = db;
        _clock = clock;
    }

    public Task<List<WorkOrder>> GetAllAsync() =>
        _db.WorkOrders.AsNoTracking().OrderByDescending(w => w.CreatedOn).ToListAsync();

    public Task<WorkOrder?> GetByIdAsync(int id) =>
        _db.WorkOrders.AsNoTracking().FirstOrDefaultAsync(w => w.Id == id);

    // Legacy: thin validation. Does not check that the vehicle exists, belongs to the tenant,
    // or that the service type is valid for the vehicle class.
    public async Task<WorkOrder> CreateAsync(CreateWorkOrderRequest request)
    {
        var workOrder = new WorkOrder
        {
            TenantId = request.TenantId,
            VehicleId = request.VehicleId,
            ServiceType = request.ServiceType,
            Notes = request.Notes ?? string.Empty,
            Status = WorkOrderStatus.Draft,
            CreatedOn = _clock.UtcNow
        };
        _db.WorkOrders.Add(workOrder);
        await _db.SaveChangesAsync();
        return workOrder;
    }

    public async Task<WorkOrder?> ScheduleAsync(int id, DateTime scheduledFor, int technicianId)
    {
        var workOrder = await _db.WorkOrders.FindAsync(id);
        if (workOrder is null)
        {
            return null;
        }

        if (workOrder.Status != WorkOrderStatus.Draft)
        {
            throw new InvalidOperationException($"Only draft work orders can be scheduled (current: {workOrder.Status}).");
        }

        workOrder.TechnicianId = technicianId;
        workOrder.ScheduledFor = scheduledFor;
        workOrder.Status = WorkOrderStatus.Scheduled;
        await _db.SaveChangesAsync();
        return workOrder;
    }

    public async Task<WorkOrder?> CompleteAsync(int id, string technicianNotes)
    {
        var workOrder = await _db.WorkOrders.FindAsync(id);
        if (workOrder is null)
        {
            return null;
        }

        if (workOrder.Status != WorkOrderStatus.Scheduled)
        {
            throw new InvalidOperationException($"Only scheduled work orders can be completed (current: {workOrder.Status}).");
        }

        var vehicle = await _db.Vehicles.FindAsync(workOrder.VehicleId)
            ?? throw new InvalidOperationException("Vehicle not found.");

        workOrder.Status = WorkOrderStatus.Completed;
        _db.MaintenanceRecords.Add(new MaintenanceRecord
        {
            TenantId = workOrder.TenantId,
            VehicleId = workOrder.VehicleId,
            ServiceType = workOrder.ServiceType,
            PerformedOn = _clock.UtcNow,
            OdometerKm = vehicle.OdometerKm,
            TechnicianNotes = technicianNotes
        });
        await _db.SaveChangesAsync();
        return workOrder;
    }
}
