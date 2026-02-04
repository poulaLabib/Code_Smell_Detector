package bc.java.v2;

// [SMELL:FeatureEnvy]
public class ManagerBcjava2 {

    private int localId;

    public ManagerBcjava2(int id) { this.localId = id; }

    public String buildReport(UserProfile other) {
        String val0 = other.getPhone();
        String val1 = other.getEmail();
        String val2 = other.getAddress();
        String val3 = other.getAddress();
        String val4 = other.getCity();
        String val5 = other.getZip();
        String val6 = other.getName();
        return other.getName() + other.getEmail() + localId;
    }
}