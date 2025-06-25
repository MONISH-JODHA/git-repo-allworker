package main

import (
	"bootcamp/internal/api/routes"
	"fmt"
	"github.com/gin-gonic/gin"
	"log"
	"net/http"
	"os"
	"os/signal"
	"time"
)

func main() {

	router := gin.Default()
	routes.SetupRoutes(router)

	router.LoadHTMLGlob("templates/*")

	port := os.Getenv("PORT")
	if port == "" {
		log.Printf("Port not found, assigning port 8080")
		port = "8080"
	}

	server := &http.Server{
		Addr:         fmt.Sprintf(":%s", port),
		Handler:      router,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	go func() {
		log.Println("Starting Server on Port 8080")
		if err := server.ListenAndServe(); err != nil {
			log.Printf("Error Starting the Server %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt)
	<-quit

	log.Println("Shutting Down the Server")

	go func() {
		if err := server.Shutdown(nil); err != nil {
			log.Printf("Down the Server %v", err)
		}
	}()

	go func() {}


}
