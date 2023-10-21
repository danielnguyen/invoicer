class Service():
    def __init__(self, service_type, reading_date, days, 
                 previous_reading, current_reading, read_type, 
                 laf, billed_consumption, unit, rate):
        self.service_type = service_type
        self.reading_date = reading_date
        self.days = days
        self.previous_reading = previous_reading
        self.current_reading = current_reading
        self.read_type = read_type
        self.laf = laf
        self.billed_consumption = billed_consumption
        self.unit = unit
        self.rate = rate
        

    def __hash__(self):
        return hash((self.service_type,
                     self.reading_date, 
                     self.days, 
                     self.previous_reading, 
                     self.current_reading, 
                     self.read_type, 
                     self.laf, 
                     self.billed_consumption, 
                     self.unit,
                     self.rate))
    
    def __eq__(self, other):
        return isinstance(other, Service) and \
               self.service_type == other.service_type and \
               self.reading_date == other.reading_date and \
               self.days == other.days and \
               self.previous_reading == other.previous_reading and \
               self.current_reading == other.current_reading and \
               self.read_type == other.read_type and \
               self.laf == other.laf and \
               self.billed_consumption == other.billed_consumption and \
               self.unit == other.unit and \
               self.rate == other.rate

    def __repr__(self):
        return (f"({self.service_type}, "
                f"{self.reading_date}, "
                f"{self.days}, "
                f"{self.previous_reading}, "
                f"{self.current_reading}, "
                f"{self.read_type}, "
                f"{self.laf}, "
                f"{self.billed_consumption}, "
                f"{self.unit}, "
                f"{self.rate})")


