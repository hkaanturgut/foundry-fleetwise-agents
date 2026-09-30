namespace FleetWise.Api.Models;

// NOTE: This is a deliberately "legacy" codebase used for spec-driven development demos.
// It works, but it carries realistic shortcuts that the demo surfaces and fixes.

public class Tenant
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public int DueSoonDays { get; set; } = 7; // FR-012
}

public class Vehicle
{
    public int Id { get; set; }
    public int TenantId { get; set; }
    public string UnitNumber { get; set; } = string.Empty;
    public string Make { get; set; } = string.Empty;
    public string Model { get; set; } = string.Empty;
    public int Year { get; set; }
    public int OdometerKm { get; set; }
    public string VehicleClass { get; set; } = "LightDuty"; // LightDuty | HeavyDuty
    public List<MaintenanceRecord> MaintenanceRecords { get; set; } = new();
}

public class MaintenanceSchedule
{
    public int Id { get; set; }
    public string VehicleClass { get; set; } = string.Empty;
    public string ServiceType { get; set; } = string.Empty; // OilChange | BrakeInspection | TireRotation | DotInspection
    public int IntervalKm { get; set; }
    public int IntervalDays { get; set; }
    public string RequiredSkill { get; set; } = string.Empty;
}

public class MaintenanceRecord
{
    public int Id { get; set; }
    public int TenantId { get; set; }
    public int VehicleId { get; set; }
    public string ServiceType { get; set; } = string.Empty;
    public DateTime PerformedOn { get; set; }
    public int OdometerKm { get; set; }
    public string TechnicianNotes { get; set; } = string.Empty;
}

public class Technician
{
    public int Id { get; set; }
    public int TenantId { get; set; }
    public string Name { get; set; } = string.Empty;
    // Legacy: skills stored as a comma-separated string.
    public string Skills { get; set; } = string.Empty;
}

public enum WorkOrderStatus
{
    Draft,
    Scheduled,
    Completed,
    Cancelled
}

public class WorkOrder
{
    public int Id { get; set; }
    public int TenantId { get; set; }
    public int VehicleId { get; set; }
    public int? TechnicianId { get; set; }
    public string ServiceType { get; set; } = string.Empty;
    public WorkOrderStatus Status { get; set; } = WorkOrderStatus.Draft;
    public DateTime CreatedOn { get; set; }
    public DateTime? ScheduledFor { get; set; }
    public string Notes { get; set; } = string.Empty;
}

public enum DispatchOutcome
{
    Approved,
    Rejected
}

/// <summary>An approval or rejection of a dispatcher suggestion (spec FR-008).</summary>
public class DispatchDecision
{
    public int Id { get; set; }
    public int TenantId { get; set; }
    public int VehicleId { get; set; }
    public string ServiceType { get; set; } = string.Empty;
    public DispatchOutcome Outcome { get; set; }
    public int? TechnicianId { get; set; }
    public int? WorkOrderId { get; set; }
    public string DecidedBy { get; set; } = string.Empty;
    public DateTime DecidedOn { get; set; }
}
