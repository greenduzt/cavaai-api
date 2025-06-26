import enum
import re
from livekit.agents import Agent, function_tool, get_job_context,RunContext
from prompts import  WELCOME_MESSAGE
from db_access import DatabaseAccess
import logging

logger = logging.getLogger("user-data")
logger.setLevel(logging.INFO)

DB = DatabaseAccess()

class CustomerDetails(enum.Enum):
    PHONE = "phone"
    NAME = "name"
    POINTS = "points" 

def normalize_phone(phone: str) -> str:
    expanded = expand_spoken_digits(phone)
    digits_only = re.sub(r'\D', '', expanded).strip()
    return digits_only

def expand_spoken_digits(spoken: str) -> str:
    spoken = spoken.lower()

    # Define patterns for double, triple, etc.
    patterns = {
        r'double (\d)': lambda m: m.group(1) * 2,
        r'triple (\d)': lambda m: m.group(1) * 3,
        r'quadruple (\d)': lambda m: m.group(1) * 4,
    }

    for pattern, replacer in patterns.items():
        spoken = re.sub(pattern, replacer, spoken)

    return spoken

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=WELCOME_MESSAGE)

        self._customer_details = {
            CustomerDetails.PHONE: "",
            CustomerDetails.NAME: "",
            CustomerDetails.POINTS: 0
        }

    def get_customer_str(self):
        customer_str = ""
        for key, value in self._customer_details.items():
            customer_str += f"{key}: {value}\n"
        
        return customer_str

    @function_tool()
    async def lookup_customer(self, context: RunContext, phone: str) -> str:
        """
        Get customer details by phone number.
        """
        normalized_phone = normalize_phone(phone)
        logger.info("Looking up customer with phone: %s", normalized_phone)

        result = DB.get_customer_by_phone(normalized_phone)
        if result is None:
            # clear out the old phone so has_customer() returns False next time
            self._customer_details[CustomerDetails.PHONE] = ""
            logger.info("No customer found with phone: %s", normalized_phone)

            return (
                "Hmm, I couldn’t find a profile for that number. "
                "Let’s try again—please say your 10-digit phone number, one digit at a time."
            )

        self._customer_details = {
            CustomerDetails.PHONE: result.phone,
            CustomerDetails.NAME: result.name,
            CustomerDetails.POINTS: result.points
        }

        return f"The customer details are:\n{self.get_customer_str()}"

    @function_tool()
    async def create_customer(self, context: RunContext, phone: str, name: str, points: int = 0) -> str:
        """
        Create a new customer with phone number, name, and optional points.
        """
        normalized_phone = normalize_phone(phone)
        logger.info("Creating customer. Original phone: %r, Normalized: %s, name: %s, points: %d", phone, normalized_phone, name, points)

        result = DB.create_customer(normalized_phone, name, int(points))
        if result is None:
            logger.error("Failed to create customer with phone: %s", normalized_phone)
            return "Failed to create customer profile. Please try again."

        self._customer_details = {
            CustomerDetails.PHONE: result.phone,
            CustomerDetails.NAME: result.name,
            CustomerDetails.POINTS: result.points
        }

        return f"Customer profile created successfully. Details:\n{self.get_customer_str()}"

    @function_tool()
    async def get_customer_details(self, context: RunContext) -> str:
        """
        Get the details of the current customer in session.
        """
        logger.info("Getting customer details")
        return f"The customer details are:\n{self.get_customer_str()}"

    def has_customer(self):
        return self._customer_details[CustomerDetails.PHONE] != ""