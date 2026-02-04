package bc.java.v3;

// [SMELL:FeatureEnvy]
public class ServiceBcjava13 {

    private int localId;

    public ServiceBcjava13(int id) { this.localId = id; }

    public String buildReport(UserProfile other) {
        String val0 = other.getAge();
        String val1 = other.getEmail();
        String val2 = other.getAge();
        String val3 = other.getZip();
        String val4 = other.getZip();
        String val5 = other.getName();
        String val6 = other.getCity();
        String val7 = other.getEmail();
        return other.getName() + other.getEmail() + localId;
    }
}