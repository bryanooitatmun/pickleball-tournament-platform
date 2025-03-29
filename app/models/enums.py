import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    PLAYER = "player"
    ORGANIZER = "organizer"
    REFEREE = "referee"

class TournamentTier(enum.Enum):
    SLATE = "SLATE"
    CUP = "CUP"
    OPEN = "OPEN"
    CHALLENGE = "CHALLENGE"

class TournamentFormat(enum.Enum):
    SINGLE_ELIMINATION = "Single Elimination"
    DOUBLE_ELIMINATION = "Double Elimination"
    ROUND_ROBIN = "Round Robin"
    GROUP_KNOCKOUT = "Group Stage + Knockout"

class TournamentStatus(enum.Enum):
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"

class CategoryType(enum.Enum):
    MENS_SINGLES = "Men's Singles"
    WOMENS_SINGLES = "Women's Singles"
    MENS_DOUBLES = "Men's Doubles"
    WOMENS_DOUBLES = "Women's Doubles"
    MIXED_DOUBLES = "Mixed Doubles"
    # For custom categories
    CUSTOM = "Custom Category"

class MatchStage(enum.Enum):
    GROUP = "group"
    KNOCKOUT = "knockout"
    PLAYOFF = "playoff"  # For 3rd place matches, etc.

class SponsorTier(enum.Enum):
    PREMIER = "Premier"
    OFFICIAL = "Official"
    FEATURED = "Featured"
    SUPPORTING = "Supporting"

class PrizeType(enum.Enum):
    CASH = "cash"
    MERCHANDISE = "merchandise"

class TicketType(enum.Enum):
    PLAYER_REPORT = "Player Report"
    GENERAL_SUPPORT = "General Support"
    TECHNICAL_ISSUE = "Technical Issue"
    PAYMENT_ISSUE = "Payment Issue"
    OTHER = "Other"

class TicketStatus(enum.Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"