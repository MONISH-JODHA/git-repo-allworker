package com.javawebtutor;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

public class DatabaseConnector {
    public static Connection getConnection() throws SQLException {
        String url = "jdbc:mysql://<RDS_ENDPOINT>:3306/jwt";  // Replace <RDS_ENDPOINT> with your AWS RDS endpoint
        String username = "your_db_username";  // AWS RDS username
        String password = "your_db_password";  // AWS RDS password
        try {
            Class.forName("com.mysql.cj.jdbc.Driver");
            return DriverManager.getConnection(url, username, password);
        } catch (ClassNotFoundException e) {
            throw new SQLException("MySQL JDBC driver not found.", e);
        }
    }
}
