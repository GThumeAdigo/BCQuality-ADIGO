table 50202 "System Configuration Log"
{
    DataClassification = SystemMetadata;

    fields
    {
        field(1; "Entry No."; Integer)
        {
        }
        field(2; "Changed By"; Code[50])
        {
            DataClassification = EndUserIdentifiableInformation;
        }
        field(3; "Change Description"; Text[250])
        {
            DataClassification = CustomerContent;
        }
        field(4; "Changed At"; DateTime)
        {
        }
    }

    keys
    {
        key(PK; "Entry No.") { Clustered = true; }
    }
}
