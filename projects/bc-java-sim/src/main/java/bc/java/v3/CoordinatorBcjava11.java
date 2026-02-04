package bc.java.v3;

// [SMELL:FeatureEnvy]
public class CoordinatorBcjava11 {

    private int localId;

    public CoordinatorBcjava11(int id) { this.localId = id; }

    public String buildReport(UserProfile other) {
        String val0 = other.getAddress();
        String val1 = other.getEmail();
        String val2 = other.getAge();
        String val3 = other.getCity();
        String val4 = other.getPhone();
        String val5 = other.getZip();
        String val6 = other.getName();
        String val7 = other.getAddress();
        String val8 = other.getPhone();
        String val9 = other.getZip();
        String val10 = other.getAddress();
        return other.getName() + other.getEmail() + localId;
    }
}