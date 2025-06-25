package routes

import (
	"bootcamp/internal/api/handlers"
	"github.com/gin-gonic/gin"
)

func SetupRoutes(router *gin.Engine) {
	router.GET("/", handlers.Home)
	router.GET("/bootcamp", handlers.Bootcamp)
}
