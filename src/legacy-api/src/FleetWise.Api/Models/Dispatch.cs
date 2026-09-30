namespace FleetWise.Api.Models;

public enum DispatchStatus
{
    Overdue,
    DueSoon,
    AlreadyHandled
}

public enum DispatchTrigger
{
    Distance,
    Date,
    NoHistory
}

/// <summary>A technician proposed for a dispatch line (populated by User Story 2).</summary>
public record TechnicianSuggestion(int? TechnicianId, string? TechnicianName, bool NoQualifiedTechnician);

/// <summary>One vehicle and one scheduled service that is overdue or due soon. Computed, not stored.</summary>
public record DispatchLine(
    int VehicleId,
    string UnitNumber,
    string ServiceType,
    DispatchStatus Status,
    DispatchTrigger Trigger,
    int? KmOverdue,
    int DaysUntilDue,
    TechnicianSuggestion? Suggestion,
    string? VehicleClass = null); // additive: lets callers (and agents) group LightDuty / HeavyDuty
