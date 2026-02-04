package commons.col.v2;

// [SMELL:FeatureEnvy]
public class EngineCommonscol7 {

    private int localId;

    public EngineCommonscol7(int id) { this.localId = id; }

    public String buildReport(UserProfile other) {
        String val0 = other.getPhone();
        String val1 = other.getZip();
        String val2 = other.getEmail();
        String val3 = other.getPhone();
        String val4 = other.getAddress();
        String val5 = other.getEmail();
        String val6 = other.getAge();
        String val7 = other.getEmail();
        String val8 = other.getEmail();
        String val9 = other.getCity();
        String val10 = other.getPhone();
        String val11 = other.getName();
        return other.getName() + other.getEmail() + localId;
    }
}